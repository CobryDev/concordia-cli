"""
LookML Base Dictionary Module

This module handles metadata extraction from BigQuery using INFORMATION_SCHEMA queries,
following the droughty pattern of treating LookML as data structures (dictionaries).
"""

from typing import List, Dict, Any, Optional
import pandas as pd
import pandas_gbq
import click
from google.cloud import bigquery
from google.api_core.exceptions import NotFound, PermissionDenied


class MetadataExtractor:
    """Extracts metadata from BigQuery using INFORMATION_SCHEMA queries with pandas-gbq."""

    def __init__(self, credentials, project_id: str, location: Optional[str] = None):
        """
        Initialize the metadata extractor.

        Args:
            credentials: Google credentials object
            project_id: GCP project ID
            location: BigQuery location/region
        """
        self.project_id = project_id
        self.location = location
        self.credentials = credentials

    def get_table_metadata(self, dataset_ids: List[str]) -> pd.DataFrame:
        """
        Extract table metadata from BigQuery INFORMATION_SCHEMA.

        Args:
            dataset_ids: List of dataset IDs to scan

        Returns:
            DataFrame containing table metadata
        """
        # Build UNION ALL query for each dataset's INFORMATION_SCHEMA
        union_queries = []
        for dataset_id in dataset_ids:
            union_queries.append(f"""
            SELECT 
                table_catalog as project_id,
                table_schema as dataset_id,
                table_name as table_id,
                table_type,
                ddl as creation_ddl,
                -- Try to extract table comment from DDL or use NULL
                CASE 
                    WHEN REGEXP_CONTAINS(ddl, r'description\\s*=\\s*"[^"]*"')
                    THEN REGEXP_EXTRACT(ddl, r'description\\s*=\\s*"([^"]*)"')
                    WHEN REGEXP_CONTAINS(ddl, r"description\\s*=\\s*'[^']*'")
                    THEN REGEXP_EXTRACT(ddl, r"description\\s*=\\s*'([^']*)'")
                    ELSE NULL
                END as table_description
            FROM `{dataset_id}.INFORMATION_SCHEMA.TABLES`
            WHERE table_type = 'BASE TABLE'
            """)

        query = " UNION ALL ".join(union_queries) + \
            "\nORDER BY dataset_id, table_id"

        try:
            click.echo("🔍 Extracting table metadata from INFORMATION_SCHEMA...")
            df = pandas_gbq.read_gbq(
                query,
                project_id=self.project_id,
                credentials=self.credentials,
                location=self.location
            )
            # Ensure we have a DataFrame
            if df is None:
                return pd.DataFrame()
            click.echo(f"✅ Found {len(df)} tables")
            return df
        except Exception as e:
            click.echo(f"❌ Error extracting table metadata: {e}")
            return pd.DataFrame()

    def get_column_metadata(self, dataset_ids: List[str]) -> pd.DataFrame:
        """
        Extract column metadata from BigQuery INFORMATION_SCHEMA.

        Args:
            dataset_ids: List of dataset IDs to scan

        Returns:
            DataFrame containing column metadata
        """
        # Build UNION ALL query for each dataset's INFORMATION_SCHEMA
        union_queries = []
        for dataset_id in dataset_ids:
            union_queries.append(f"""
            SELECT 
                table_catalog as project_id,
                table_schema as dataset_id,
                table_name as table_id,
                column_name,
                ordinal_position,
                is_nullable,
                data_type,
                is_generated,
                generation_expression,
                is_stored,
                is_hidden,
                is_updatable,
                is_system_defined,
                is_partitioning_column,
                clustering_ordinal_position,
                collation_name,
                column_default,
                -- Column description/comment (not available in INFORMATION_SCHEMA.COLUMNS)
                CAST(NULL AS STRING) as column_description,
                -- Full table identifier for joining
                CONCAT(table_catalog, '.', table_schema, '.', table_name) as full_table_id
            FROM `{dataset_id}.INFORMATION_SCHEMA.COLUMNS`
            """)

        query = " UNION ALL ".join(
            union_queries) + "\nORDER BY dataset_id, table_id, ordinal_position"

        try:
            click.echo(
                "🔍 Extracting column metadata from INFORMATION_SCHEMA...")
            df = pandas_gbq.read_gbq(
                query,
                project_id=self.project_id,
                credentials=self.credentials,
                location=self.location
            )
            # Ensure we have a DataFrame
            if df is None:
                return pd.DataFrame()
            click.echo(f"✅ Found {len(df)} columns")
            return df
        except Exception as e:
            click.echo(f"❌ Error extracting column metadata: {e}")
            return pd.DataFrame()

    def get_primary_key_metadata(self, dataset_ids: List[str]) -> pd.DataFrame:
        """
        Extract primary key metadata from BigQuery INFORMATION_SCHEMA.

        Args:
            dataset_ids: List of dataset IDs to scan

        Returns:
            DataFrame containing primary key metadata
        """
        # Build UNION ALL query for each dataset's INFORMATION_SCHEMA
        union_queries = []
        for dataset_id in dataset_ids:
            union_queries.append(f"""
            SELECT 
                constraint_catalog as project_id,
                constraint_schema as dataset_id,
                table_name as table_id,
                constraint_name,
                constraint_type,
                is_deferrable,
                initially_deferred,
                enforced
            FROM `{dataset_id}.INFORMATION_SCHEMA.TABLE_CONSTRAINTS`
            WHERE constraint_type = 'PRIMARY KEY'
            """)

        query = " UNION ALL ".join(union_queries) + \
            "\nORDER BY dataset_id, table_id"

        try:
            click.echo(
                "🔍 Extracting primary key metadata from INFORMATION_SCHEMA...")
            df = pandas_gbq.read_gbq(
                query,
                project_id=self.project_id,
                credentials=self.credentials,
                location=self.location
            )
            # Ensure we have a DataFrame
            if df is None:
                return pd.DataFrame()
            click.echo(f"✅ Found {len(df)} primary key constraints")
            return df
        except Exception as e:
            click.echo(f"❌ Error extracting primary key metadata: {e}")
            return pd.DataFrame()

    def wrangle_metadata(self, tables_df: pd.DataFrame, columns_df: pd.DataFrame,
                         primary_keys_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Wrangle and combine the extracted metadata using pandas.

        Args:
            tables_df: DataFrame containing table metadata
            columns_df: DataFrame containing column metadata
            primary_keys_df: DataFrame containing primary key metadata

        Returns:
            Dictionary containing processed metadata ready for LookML generation
        """
        if tables_df.empty or columns_df.empty:
            return {}

        click.echo("🔧 Wrangling metadata...")

        # Merge tables with columns
        merged_df = pd.merge(
            tables_df,
            columns_df,
            on=['project_id', 'dataset_id', 'table_id'],
            how='inner'
        )

        # Add primary key information
        if not primary_keys_df.empty:
            pk_columns = self._get_primary_key_columns(primary_keys_df)
            merged_df['is_primary_key'] = merged_df.apply(
                lambda row: self._is_column_primary_key(row, pk_columns), axis=1
            )
        else:
            merged_df['is_primary_key'] = False

        # Standardize data types
        merged_df['standardized_type'] = merged_df['data_type'].apply(
            self._standardize_data_type)

        # Group by table to create table-level metadata
        tables_metadata = {}

        for (project_id, dataset_id, table_id), group in merged_df.groupby(['project_id', 'dataset_id', 'table_id']):
            table_key = f"{dataset_id}.{table_id}"

            # Sort columns by ordinal position
            group_sorted = group.sort_values('ordinal_position')

            tables_metadata[table_key] = {
                'project_id': project_id,
                'dataset_id': dataset_id,
                'table_id': table_id,
                'table_description': group_sorted.iloc[0]['table_description'],
                'columns': []
            }

            for _, column in group_sorted.iterrows():
                column_info = {
                    'name': column['column_name'],
                    'type': column['data_type'],
                    'standardized_type': column['standardized_type'],
                    'mode': 'REQUIRED' if column['is_nullable'] == 'NO' else 'NULLABLE',
                    'description': column['column_description'],
                    'is_primary_key': column['is_primary_key'],
                    'ordinal_position': column['ordinal_position']
                }
                tables_metadata[table_key]['columns'].append(column_info)

        click.echo(f"✅ Processed metadata for {len(tables_metadata)} tables")
        return tables_metadata

    def _get_primary_key_columns(self, primary_keys_df: pd.DataFrame) -> Dict[str, List[str]]:
        """Extract primary key column information."""
        # This would need a separate query to get the actual column names for constraints
        # For now, return empty dict - this can be enhanced later
        return {}

    def _is_column_primary_key(self, row: pd.Series, pk_columns: Dict[str, List[str]]) -> bool:
        """Check if a column is part of a primary key."""
        table_key = f"{row['dataset_id']}.{row['table_id']}"
        return row['column_name'] in pk_columns.get(table_key, [])

    def _standardize_data_type(self, bq_type: str) -> str:
        """
        Standardize BigQuery data types for consistent processing.

        Args:
            bq_type: BigQuery data type

        Returns:
            Standardized type string
        """
        type_mapping = {
            'STRING': 'string',
            'BYTES': 'string',
            'INTEGER': 'number',
            'INT64': 'number',
            'FLOAT': 'number',
            'FLOAT64': 'number',
            'NUMERIC': 'number',
            'BIGNUMERIC': 'number',
            'BOOLEAN': 'yesno',
            'BOOL': 'yesno',
            'TIMESTAMP': 'datetime',
            'DATETIME': 'datetime',
            'DATE': 'date',
            'TIME': 'time',
            'GEOGRAPHY': 'string',
            'JSON': 'string',
            'ARRAY': 'string',
            'STRUCT': 'string',
            'RECORD': 'string'
        }

        return type_mapping.get(bq_type.upper(), 'string')
