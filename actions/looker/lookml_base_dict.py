"""
LookML Base Dictionary Module

This module handles metadata extraction from BigQuery using INFORMATION_SCHEMA queries,
following the droughty pattern of treating LookML as data structures (dictionaries).
"""

import re
from typing import Optional

import click
import pandas as pd
import pandas_gbq

from ..models.config import VALID_BIGQUERY_TABLE_TYPES
from ..models.metadata import ColumnMetadata, MetadataCollection, TableMetadata


class MetadataExtractor:
    """Extracts metadata from BigQuery using INFORMATION_SCHEMA queries with pandas-gbq."""

    def __init__(
        self,
        credentials,
        project_id: str,
        location: Optional[str] = None,
        table_types: Optional[list[str]] = None,
    ):
        """
        Initialize the metadata extractor.

        Args:
            credentials: Google credentials object
            project_id: GCP project ID
            location: BigQuery location/region
            table_types: BigQuery INFORMATION_SCHEMA table types to include
        """
        self.project_id = project_id
        self.location = location
        self.credentials = credentials
        self.table_types = self._validate_table_types(table_types if table_types is not None else ["BASE TABLE"])

    def get_table_metadata(self, dataset_ids: list[str]) -> pd.DataFrame:
        """
        Extract table metadata from BigQuery INFORMATION_SCHEMA.

        Args:
            dataset_ids: List of dataset IDs to scan

        Returns:
            DataFrame containing table metadata
        """
        # Build UNION ALL query for each dataset's INFORMATION_SCHEMA
        union_queries = []
        table_type_filter = self._table_type_filter_sql()
        for dataset_id in dataset_ids:
            safe_dataset_id = self._validate_dataset_id(dataset_id)
            sql = f"""
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
            FROM `{safe_dataset_id}`.INFORMATION_SCHEMA.TABLES
            WHERE table_type IN ({table_type_filter})
            """  # noqa: S608 - dataset identifier validated by _validate_dataset_id
            union_queries.append(sql)

        query = " UNION ALL ".join(union_queries) + "\nORDER BY dataset_id, table_id"

        try:
            click.echo("🔍 Extracting table metadata from INFORMATION_SCHEMA...")
            df = pandas_gbq.read_gbq(
                query,
                project_id=self.project_id,
                credentials=self.credentials,
                location=self.location,
            )
            # Ensure we have a DataFrame
            if df is None:
                return pd.DataFrame()
            # Convert to DataFrame if it's a Series
            if isinstance(df, pd.Series):
                df = df.to_frame().T
            click.echo(f"✅ Found {len(df)} BigQuery objects")
            return df
        except Exception as e:
            click.echo(f"❌ Error extracting table metadata: {e}")
            return pd.DataFrame()

    def get_column_metadata(self, dataset_ids: list[str]) -> pd.DataFrame:
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
            safe_dataset_id = self._validate_dataset_id(dataset_id)
            sql = f"""
            SELECT
                c.table_catalog as project_id,
                c.table_schema as dataset_id,
                c.table_name as table_id,
                c.column_name,
                c.ordinal_position,
                c.is_nullable,
                c.data_type,
                c.is_generated,
                c.generation_expression,
                c.is_stored,
                c.is_hidden,
                c.is_updatable,
                c.is_system_defined,
                c.is_partitioning_column,
                c.clustering_ordinal_position,
                c.collation_name,
                c.column_default,
                -- Column description from COLUMN_FIELD_PATHS view
                cfp.description as column_description,
                -- Full table identifier for joining
                CONCAT(c.table_catalog, '.', c.table_schema, '.', c.table_name) as full_table_id
            FROM `{safe_dataset_id}`.INFORMATION_SCHEMA.COLUMNS c
            LEFT JOIN `{safe_dataset_id}`.INFORMATION_SCHEMA.COLUMN_FIELD_PATHS cfp
                ON c.table_catalog = cfp.table_catalog
                AND c.table_schema = cfp.table_schema
                AND c.table_name = cfp.table_name
                AND c.column_name = cfp.column_name
                AND cfp.field_path = cfp.column_name  -- Only get top-level column descriptions
            """  # noqa: S608 - dataset identifier validated by _validate_dataset_id
            union_queries.append(sql)

        query = " UNION ALL ".join(union_queries) + "\nORDER BY dataset_id, table_id, ordinal_position"

        try:
            click.echo("🔍 Extracting column metadata from INFORMATION_SCHEMA...")
            df = pandas_gbq.read_gbq(
                query,
                project_id=self.project_id,
                credentials=self.credentials,
                location=self.location,
            )
            # Ensure we have a DataFrame
            if df is None:
                return pd.DataFrame()
            # Convert to DataFrame if it's a Series
            if isinstance(df, pd.Series):
                df = df.to_frame().T
            click.echo(f"✅ Found {len(df)} columns")
            return df
        except Exception as e:
            click.echo(f"❌ Error extracting column metadata: {e}")
            return pd.DataFrame()

    def get_primary_key_metadata(self, dataset_ids: list[str]) -> pd.DataFrame:
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
            safe_dataset_id = self._validate_dataset_id(dataset_id)
            sql = f"""
            SELECT
                constraint_catalog as project_id,
                constraint_schema as dataset_id,
                table_name as table_id,
                constraint_name,
                constraint_type,
                is_deferrable,
                initially_deferred,
                enforced
            FROM `{safe_dataset_id}`.INFORMATION_SCHEMA.TABLE_CONSTRAINTS
            WHERE constraint_type = 'PRIMARY KEY'
            """  # noqa: S608 - dataset identifier validated by _validate_dataset_id
            union_queries.append(sql)

        query = " UNION ALL ".join(union_queries) + "\nORDER BY dataset_id, table_id"

        try:
            click.echo("🔍 Extracting primary key metadata from INFORMATION_SCHEMA...")
            df = pandas_gbq.read_gbq(
                query,
                project_id=self.project_id,
                credentials=self.credentials,
                location=self.location,
            )
            # Ensure we have a DataFrame
            if df is None:
                return pd.DataFrame()
            # Convert to DataFrame if it's a Series
            if isinstance(df, pd.Series):
                df = df.to_frame().T
            click.echo(f"✅ Found {len(df)} primary key constraints")
            return df
        except Exception as e:
            click.echo(f"❌ Error extracting primary key metadata: {e}")
            return pd.DataFrame()

    def wrangle_metadata(
        self,
        tables_df: pd.DataFrame,
        columns_df: pd.DataFrame,
        primary_keys_df: pd.DataFrame,
    ) -> MetadataCollection:
        """
        Wrangle and combine the extracted metadata using pandas.

        Args:
            tables_df: DataFrame containing table metadata
            columns_df: DataFrame containing column metadata
            primary_keys_df: DataFrame containing primary key metadata

        Returns:
            MetadataCollection containing type-safe table metadata
        """
        if tables_df.empty or columns_df.empty:
            return MetadataCollection(tables={})

        click.echo("🔧 Wrangling metadata...")

        # Merge tables with columns
        merged_df = pd.merge(
            tables_df,
            columns_df,
            on=["project_id", "dataset_id", "table_id"],
            how="inner",
        )

        # Add primary key information
        if not primary_keys_df.empty:
            pk_columns = self._get_primary_key_columns(primary_keys_df)
            merged_df["is_primary_key"] = merged_df.apply(
                lambda row: self._is_column_primary_key(row, pk_columns), axis=1
            )
        else:
            merged_df["is_primary_key"] = False

        # Standardize data types
        merged_df["standardized_type"] = merged_df["data_type"].apply(self._standardize_data_type)

        # Group by table to create table-level metadata with Pydantic models
        metadata_collection = MetadataCollection(tables={})

        for (project_id, dataset_id, table_id), group in merged_df.groupby(["project_id", "dataset_id", "table_id"]):
            # Sort columns by ordinal position
            group_sorted = group.sort_values("ordinal_position")

            # Create column metadata objects
            columns = []
            for _, column in group_sorted.iterrows():
                column_metadata = ColumnMetadata(
                    name=str(column["column_name"]),
                    type=str(column["data_type"]),
                    standardized_type=str(column["standardized_type"]),
                    description=(str(column["column_description"]) if pd.notna(column["column_description"]) else None),
                    is_primary_key=bool(column["is_primary_key"]),
                    is_nullable=column["is_nullable"] == "YES",
                    ordinal_position=(
                        int(column["ordinal_position"]) if pd.notna(column["ordinal_position"]) else None
                    ),
                )
                columns.append(column_metadata)

            # Create table metadata object
            table_description = group_sorted.iloc[0]["table_description"]
            table_type = group_sorted.iloc[0]["table_type"]
            creation_ddl = group_sorted.iloc[0]["creation_ddl"]
            table_metadata = TableMetadata(
                table_id=table_id,
                dataset_id=dataset_id,
                project_id=project_id,
                table_description=(str(table_description) if pd.notna(table_description) else None),
                table_type=str(table_type),
                columns=columns,
                creation_ddl=(str(creation_ddl) if pd.notna(creation_ddl) else None),
            )

            metadata_collection.add_table(table_metadata)

        click.echo(f"✅ Processed metadata for {metadata_collection.table_count()} BigQuery objects")
        return metadata_collection

    def _get_primary_key_columns(self, primary_keys_df: pd.DataFrame) -> dict[str, list[str]]:
        """Extract primary key column information."""
        # This would need a separate query to get the actual column names for constraints
        # For now, return empty dict - this can be enhanced later
        return {}

    def _is_column_primary_key(self, row: pd.Series, pk_columns: dict[str, list[str]]) -> bool:
        """Check if a column is part of a primary key."""
        table_key = f"{row['dataset_id']}.{row['table_id']}"
        return row["column_name"] in pk_columns.get(table_key, [])

    def _standardize_data_type(self, bq_type: str) -> str:
        """
        Standardize BigQuery data types for consistent processing.

        Args:
            bq_type: BigQuery data type

        Returns:
            Standardized type string
        """
        type_mapping = {
            "STRING": "STRING",
            "BYTES": "STRING",
            "INTEGER": "INTEGER",
            "INT64": "INT64",
            "FLOAT": "FLOAT64",
            "FLOAT64": "FLOAT64",
            "NUMERIC": "NUMERIC",
            "BIGNUMERIC": "BIGNUMERIC",
            "BOOLEAN": "BOOL",
            "BOOL": "BOOL",
            "TIMESTAMP": "TIMESTAMP",
            "DATETIME": "DATETIME",
            "DATE": "DATE",
            "TIME": "TIME",
            "GEOGRAPHY": "STRING",
            "JSON": "STRING",
            "ARRAY": "STRING",
            "STRUCT": "STRING",
            "RECORD": "STRING",
        }

        return type_mapping.get(bq_type.upper(), "STRING")

    def _validate_dataset_id(self, dataset_id: str) -> str:
        """
        Validate a BigQuery dataset identifier to prevent SQL injection through identifiers.

        BigQuery dataset IDs may contain letters, numbers, and underscores.
        This validator enforces:
        - Only [A-Za-z0-9_]
        - Starts with a letter or underscore
        - Length 1..1024
        - No dots/backticks or other quoting characters
        """
        if not isinstance(dataset_id, str):
            raise ValueError("Dataset ID must be a string")

        if len(dataset_id) == 0 or len(dataset_id) > 1024:
            raise ValueError("Dataset ID length must be between 1 and 1024 characters")

        if "`" in dataset_id or "." in dataset_id:
            raise ValueError("Dataset ID must not contain quotes or dots")

        pattern = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
        if not pattern.match(dataset_id):
            raise ValueError(
                "Dataset ID must start with a letter or underscore, and contain only letters, numbers, and underscores"
            )

        return dataset_id

    def _validate_table_types(self, table_types: list[str]) -> list[str]:
        """Validate BigQuery table types before interpolating them into SQL."""
        if not isinstance(table_types, list):
            raise ValueError("Table types must be provided as a list")

        normalized_table_types = []
        for table_type in table_types:
            if not isinstance(table_type, str):
                raise ValueError("Table types must be strings")

            normalized_table_type = table_type.strip().upper()
            if not normalized_table_type:
                raise ValueError("Table types cannot be empty or whitespace only")

            if normalized_table_type not in VALID_BIGQUERY_TABLE_TYPES:
                raise ValueError(
                    f"Invalid BigQuery table type '{table_type}'. "
                    f"Must be one of: {', '.join(sorted(VALID_BIGQUERY_TABLE_TYPES))}."
                )
            if normalized_table_type not in normalized_table_types:
                normalized_table_types.append(normalized_table_type)

        if not normalized_table_types:
            raise ValueError("At least one BigQuery table type must be specified")

        return normalized_table_types

    def _table_type_filter_sql(self) -> str:
        """Build a safe SQL literal list for the table type filter."""
        return ", ".join(f"'{table_type}'" for table_type in self.table_types)
