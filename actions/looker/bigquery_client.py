from typing import Any, Optional

import click
from google.api_core.exceptions import NotFound, PermissionDenied
from google.cloud import bigquery

from .field_utils import FieldIdentifier
from .lookml_base_dict import MetadataExtractor


class ErrorTracker:
    """Tracks and categorizes errors during BigQuery operations."""

    def __init__(self):
        self.dataset_errors = []
        self.table_errors = []
        self.permission_errors = []
        self.not_found_errors = []
        self.connection_errors = []
        self.unexpected_errors = []

    def add_dataset_error(self, dataset_id: str, error: Exception, error_type: str = "unexpected"):
        """Add a dataset-level error."""
        error_info = {
            "dataset_id": dataset_id,
            "error": str(error),
            "error_type": error_type,
            "exception_type": type(error).__name__,
        }

        if error_type == "permission":
            self.permission_errors.append(error_info)
        elif error_type == "not_found":
            self.not_found_errors.append(error_info)
        elif error_type == "connection":
            self.connection_errors.append(error_info)
        else:
            self.dataset_errors.append(error_info)

    def add_table_error(
        self,
        dataset_id: str,
        table_id: str,
        error: Exception,
        error_type: str = "unexpected",
    ):
        """Add a table-level error."""
        error_info = {
            "dataset_id": dataset_id,
            "table_id": table_id,
            "full_table_id": f"{dataset_id}.{table_id}",
            "error": str(error),
            "error_type": error_type,
            "exception_type": type(error).__name__,
        }

        if error_type == "permission":
            self.permission_errors.append(error_info)
        elif error_type == "not_found":
            self.not_found_errors.append(error_info)
        else:
            self.table_errors.append(error_info)

    def has_errors(self) -> bool:
        """Check if any errors were recorded."""
        return bool(
            self.dataset_errors
            or self.table_errors
            or self.permission_errors
            or self.not_found_errors
            or self.connection_errors
            or self.unexpected_errors
        )

    def get_total_error_count(self) -> int:
        """Get the total number of errors recorded."""
        return (
            len(self.dataset_errors)
            + len(self.table_errors)
            + len(self.permission_errors)
            + len(self.not_found_errors)
            + len(self.connection_errors)
            + len(self.unexpected_errors)
        )

    def print_summary(self, total_datasets: int, total_tables_found: int):
        """Print a comprehensive error summary."""
        if not self.has_errors():
            click.echo("✅ No errors encountered during BigQuery operations")
            return

        click.echo("\n" + "=" * 60)
        click.echo("📊 OPERATION SUMMARY")
        click.echo("=" * 60)

        # Success stats
        successful_datasets = (
            total_datasets
            - len(self.dataset_errors)
            - len([e for e in self.not_found_errors + self.permission_errors if "table_id" not in e])
        )
        successful_tables = total_tables_found

        click.echo(
            f"✅ Successful: {successful_datasets}/{total_datasets} datasets, {successful_tables} tables processed"
        )

        if self.has_errors():
            click.echo(f"❌ Errors: {self.get_total_error_count()} total errors encountered")

        # Detailed error breakdown
        if self.permission_errors:
            click.echo(f"\n🔒 Permission Denied ({len(self.permission_errors)}):")
            for error in self.permission_errors:
                if "table_id" in error:
                    click.echo(f"   • Table: {error['full_table_id']}")
                else:
                    click.echo(f"   • Dataset: {error['dataset_id']}")

        if self.not_found_errors:
            click.echo(f"\n🔍 Not Found ({len(self.not_found_errors)}):")
            for error in self.not_found_errors:
                if "table_id" in error:
                    click.echo(f"   • Table: {error['full_table_id']}")
                else:
                    click.echo(f"   • Dataset: {error['dataset_id']}")

        if self.dataset_errors:
            click.echo(f"\n📁 Dataset Errors ({len(self.dataset_errors)}):")
            for error in self.dataset_errors:
                click.echo(f"   • Dataset: {error['dataset_id']}")
                click.echo(f"     Error: {error['error']}")

        if self.table_errors:
            click.echo(f"\n📋 Table Errors ({len(self.table_errors)}):")
            for error in self.table_errors:
                click.echo(f"   • Table: {error['full_table_id']}")
                click.echo(f"     Error: {error['error']}")

        if self.connection_errors:
            click.echo(f"\n🔗 Connection Errors ({len(self.connection_errors)}):")
            for error in self.connection_errors:
                click.echo(f"   • {error['error']}")

        click.echo("=" * 60)


class TableInfo:
    """Represents a BigQuery table with its schema information."""

    def __init__(self, dataset_id: str, table_id: str, description: Optional[str] = None):
        self.dataset_id = dataset_id
        self.table_id = table_id
        self.full_table_id = f"{dataset_id}.{table_id}"
        self.description = description
        self.columns: list[dict[str, Any]] = []

    def add_column(
        self,
        name: str,
        data_type: str,
        mode: str = "NULLABLE",
        description: Optional[str] = None,
    ):
        """Add a column to the table schema."""
        self.columns.append({"name": name, "type": data_type, "mode": mode, "description": description})


class BigQueryClient:
    """
    Client for interacting with BigQuery to fetch table schemas using pandas-gbq.
    Following the droughty pattern of using INFORMATION_SCHEMA queries.
    """

    def __init__(
        self,
        credentials,
        project_id: str,
        location: Optional[str] = None,
        config: Optional[dict[str, Any]] = None,
    ):
        """
        Initialize BigQuery client.

        Args:
            credentials: Google credentials object
            project_id: GCP project ID
            location: BigQuery location/region
            config: Configuration dictionary containing naming conventions
        """
        self.project_id = project_id
        self.location = location
        self.credentials = credentials
        self.config = config or {}
        self.model_rules = self.config.get("model_rules", {})
        self.field_identifier = FieldIdentifier(self.model_rules)
        self.client = bigquery.Client(credentials=credentials, project=project_id, location=location)
        self.error_tracker = ErrorTracker()

        # Initialize the metadata extractor
        self.metadata_extractor = MetadataExtractor(credentials, project_id, location)

    def get_tables_metadata(self, dataset_ids: list[str]) -> dict[str, dict[str, Any]]:
        """
        Get metadata for all tables from the specified datasets using INFORMATION_SCHEMA.

        Args:
            dataset_ids: List of dataset IDs to scan

        Returns:
            Dictionary containing table metadata
        """
        try:
            # Extract metadata using INFORMATION_SCHEMA queries
            tables_df = self.metadata_extractor.get_table_metadata(dataset_ids)
            columns_df = self.metadata_extractor.get_column_metadata(dataset_ids)
            primary_keys_df = self.metadata_extractor.get_primary_key_metadata(dataset_ids)

            # Wrangle the metadata into a usable format
            metadata_collection = self.metadata_extractor.wrangle_metadata(tables_df, columns_df, primary_keys_df)

            click.echo(f"📊 Successfully processed {metadata_collection.table_count()} tables")
            # Convert TableMetadata objects to dictionaries
            return {key: table.model_dump() for key, table in metadata_collection.tables.items()}

        except Exception as e:
            click.echo(f"❌ Error extracting table metadata: {e}")
            self.error_tracker.add_dataset_error("all", e, "metadata_extraction")
            return {}

    def get_tables_in_datasets(self, dataset_ids: list[str]) -> list[TableInfo]:
        """
        Get all tables from the specified datasets (backward compatibility).

        Args:
            dataset_ids: List of dataset IDs to scan

        Returns:
            List of TableInfo objects with their schemas
        """
        # For backward compatibility, convert metadata to TableInfo objects
        tables_metadata = self.get_tables_metadata(dataset_ids)
        table_info_list = []

        for _table_key, table_data in tables_metadata.items():
            table_info = TableInfo(
                dataset_id=table_data["dataset_id"],
                table_id=table_data["table_id"],
                description=table_data.get("table_description"),
            )

            # Add columns
            for column in table_data["columns"]:
                table_info.add_column(
                    name=column["name"],
                    data_type=column["type"],
                    mode=column["mode"],
                    description=column.get("description"),
                )

            table_info_list.append(table_info)

        return table_info_list

    def get_dataset_info(self, dataset_ids: list[str]) -> dict[str, dict[str, Any]]:
        """
        Get detailed information about datasets using pandas-gbq.

        Args:
            dataset_ids: List of dataset IDs to analyze

        Returns:
            Dictionary containing dataset information
        """
        dataset_info = {}

        for dataset_id in dataset_ids:
            try:
                # Get dataset metadata
                dataset = self.client.get_dataset(dataset_id)
                dataset_info[dataset_id] = {
                    "dataset_id": dataset_id,
                    "description": dataset.description,
                    "location": dataset.location,
                    "created": dataset.created,
                    "modified": dataset.modified,
                    "friendly_name": dataset.friendly_name,
                }

            except NotFound:
                click.echo(f"   ❌ Dataset '{dataset_id}' not found")
                self.error_tracker.add_dataset_error(
                    dataset_id,
                    Exception(f"Dataset {dataset_id} not found"),
                    "not_found",
                )
            except PermissionDenied:
                click.echo(f"   ❌ Permission denied to access dataset '{dataset_id}'")
                self.error_tracker.add_dataset_error(
                    dataset_id,
                    Exception(f"Permission denied for dataset {dataset_id}"),
                    "permission",
                )
            except Exception as e:
                click.echo(f"   ❌ Error accessing dataset '{dataset_id}': {e}")
                self.error_tracker.add_dataset_error(dataset_id, e, "unexpected")

        return dataset_info

    def analyze_table_relationships(
        self, tables_metadata: dict[str, dict[str, Any]]
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Analyze relationships between tables based on foreign key patterns.

        Args:
            tables_metadata: Dictionary of table metadata

        Returns:
            Dictionary containing relationship information
        """
        relationships = {}

        for table_key, table_data in tables_metadata.items():
            table_relationships = []

            for column in table_data["columns"]:
                column_name = column["name"]

                # Look for foreign key patterns
                if self._is_foreign_key(column_name):
                    # Try to find the referenced table
                    potential_table = self._infer_referenced_table(column_name, tables_metadata)
                    if potential_table:
                        table_relationships.append(
                            {
                                "column": column_name,
                                "referenced_table": potential_table,
                                "relationship_type": "many_to_one",
                            }
                        )

            if table_relationships:
                relationships[table_key] = table_relationships

        return relationships

    def _infer_referenced_table(self, column_name: str, tables_metadata: dict[str, dict[str, Any]]) -> Optional[str]:
        """Infer the referenced table from a foreign key column name."""
        # Remove configured suffixes
        base_name = column_name
        fk_suffix = self.field_identifier.get_foreign_key_suffix()

        if base_name.endswith(fk_suffix):
            base_name = base_name[: -len(fk_suffix)]
        # Keep backward compatibility with _id suffix
        elif base_name.endswith("_id"):
            base_name = base_name[:-3]

        # Look for matching table (try plural forms)
        potential_names = [
            base_name,
            base_name + "s",
            base_name + "es",
            base_name[:-1] + "ies" if base_name.endswith("y") else None,
        ]

        for table_key in tables_metadata.keys():
            table_id = tables_metadata[table_key]["table_id"]
            for potential_name in potential_names:
                if potential_name and table_id.lower() == potential_name.lower():
                    return table_key

        return None

    def get_error_tracker(self) -> ErrorTracker:
        """Get the error tracker instance."""
        return self.error_tracker

    def test_connection(self, dataset_ids: list[str]) -> bool:
        """
        Test the BigQuery connection and dataset access.

        Args:
            dataset_ids: List of dataset IDs to test access for

        Returns:
            True if connection and access are successful
        """
        try:
            # Test basic connection
            self.client.query("SELECT 1").result()
            click.echo("✅ BigQuery connection successful")

            # Test dataset access
            accessible_datasets = []
            for dataset_id in dataset_ids:
                try:
                    self.client.get_dataset(dataset_id)
                    accessible_datasets.append(dataset_id)
                    click.echo(f"✅ Dataset '{dataset_id}' accessible")
                except NotFound:
                    click.echo(f"❌ Dataset '{dataset_id}' not found")
                except PermissionDenied:
                    click.echo(f"❌ Permission denied to access dataset '{dataset_id}'")
                except Exception as e:
                    click.echo(f"❌ Error accessing dataset '{dataset_id}': {e}")

            if not accessible_datasets:
                click.echo("❌ No accessible datasets found")
                return False

            return True

        except Exception as e:
            click.echo(f"❌ BigQuery connection failed: {e}")
            return False

    def _is_foreign_key(self, field_name: str) -> bool:
        """Check if a field is a foreign key based on naming conventions."""
        return self.field_identifier.is_foreign_key(field_name)

    def _is_primary_key(self, field_name: str) -> bool:
        """Check if a field is a primary key based on naming conventions."""
        return self.field_identifier.is_primary_key(field_name)
