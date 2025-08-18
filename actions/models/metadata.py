"""
Pydantic models for table and column metadata.

These models provide type safety for metadata structures returned from
BigQuery INFORMATION_SCHEMA queries, replacing Dict[str, Any] usage.
"""

from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class ColumnMetadata(BaseModel):
    """Metadata for a single BigQuery column."""

    name: str = Field(description="Column name")
    type: str = Field(description="BigQuery column type")
    standardized_type: str = Field(description="Standardized type for processing")
    description: Optional[str] = Field(default=None, description="Column description from BigQuery")
    is_primary_key: bool = Field(default=False, description="Whether this column is identified as a primary key")
    is_foreign_key: bool = Field(default=False, description="Whether this column is identified as a foreign key")
    is_nullable: bool = Field(default=True, description="Whether the column allows NULL values")
    ordinal_position: Optional[int] = Field(default=None, description="Position of column in table schema")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        """Ensure column name is not empty."""
        if not v or not v.strip():
            raise ValueError("Column name cannot be empty")
        return v.strip()

    @field_validator("type", "standardized_type")
    @classmethod
    def validate_types(cls, v):
        """Ensure types are uppercase."""
        return v.upper() if v else v

    def is_time_type(self) -> bool:
        """Check if this is a time-based column type."""
        time_types = {"TIMESTAMP", "DATETIME", "DATE", "TIME"}
        return self.standardized_type in time_types

    def is_numeric_type(self) -> bool:
        """Check if this is a numeric column type."""
        numeric_types = {
            "INTEGER",
            "INT64",
            "FLOAT64",
            "NUMERIC",
            "DECIMAL",
            "BIGNUMERIC",
        }
        return self.standardized_type in numeric_types

    def is_string_type(self) -> bool:
        """Check if this is a string column type."""
        string_types = {"STRING", "TEXT"}
        return self.standardized_type in string_types

    def is_boolean_type(self) -> bool:
        """Check if this is a boolean column type."""
        return self.standardized_type == "BOOL"


class TableMetadata(BaseModel):
    """Metadata for a single BigQuery table."""

    table_id: str = Field(description="Table name")
    dataset_id: str = Field(description="Dataset ID containing the table")
    project_id: str = Field(description="GCP project ID")
    table_description: Optional[str] = Field(default=None, description="Table description from BigQuery")
    table_type: str = Field(default="BASE TABLE", description="Type of table (BASE TABLE, VIEW, etc.)")
    columns: list[ColumnMetadata] = Field(description="List of column metadata")
    creation_ddl: Optional[str] = Field(default=None, description="DDL used to create the table")

    @field_validator("table_id", "dataset_id", "project_id")
    @classmethod
    def validate_identifiers(cls, v):
        """Ensure identifiers are not empty."""
        if not v or not v.strip():
            raise ValueError("Identifier cannot be empty")
        return v.strip()

    @property
    def full_table_name(self) -> str:
        """Get fully qualified table name."""
        return f"{self.project_id}.{self.dataset_id}.{self.table_id}"

    @property
    def table_key(self) -> str:
        """Get table key for referencing."""
        return f"{self.dataset_id}.{self.table_id}"

    def get_primary_key_columns(self) -> list[ColumnMetadata]:
        """Get columns that are marked as primary keys."""
        return [col for col in self.columns if col.is_primary_key]

    def get_foreign_key_columns(self) -> list[ColumnMetadata]:
        """Get columns that are marked as foreign keys."""
        return [col for col in self.columns if col.is_foreign_key]

    def get_columns_by_type(self, column_type: str) -> list[ColumnMetadata]:
        """Get columns of a specific type."""
        return [col for col in self.columns if col.standardized_type == column_type]

    def get_column_by_name(self, name: str) -> Optional[ColumnMetadata]:
        """Get a specific column by name."""
        for col in self.columns:
            if col.name == name:
                return col
        return None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for backward compatibility."""
        return {
            "table_id": self.table_id,
            "dataset_id": self.dataset_id,
            "project_id": self.project_id,
            "table_description": self.table_description,
            "table_type": self.table_type,
            "columns": [col.model_dump() for col in self.columns],
            "creation_ddl": self.creation_ddl,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TableMetadata":
        """Create instance from dictionary."""
        # Convert columns from dicts to ColumnMetadata objects
        if "columns" in data and data["columns"] and isinstance(data["columns"][0], dict):
            data = data.copy()
            data["columns"] = [ColumnMetadata(**col) for col in data["columns"]]
        return cls(**data)


class MetadataCollection(BaseModel):
    """Collection of table metadata with helper methods."""

    tables: dict[str, TableMetadata] = Field(description="Dictionary of table metadata keyed by table_key")

    def add_table(self, table: TableMetadata) -> None:
        """Add a table to the collection."""
        self.tables[table.table_key] = table

    def get_table(self, table_key: str) -> Optional[TableMetadata]:
        """Get a table by its key."""
        return self.tables.get(table_key)

    def get_tables_by_dataset(self, dataset_id: str) -> list[TableMetadata]:
        """Get all tables from a specific dataset."""
        return [table for table in self.tables.values() if table.dataset_id == dataset_id]

    def get_all_tables(self) -> list[TableMetadata]:
        """Get all tables as a list."""
        return list(self.tables.values())

    def table_count(self) -> int:
        """Get total number of tables."""
        return len(self.tables)

    def to_dict(self) -> dict[str, dict[str, Any]]:
        """Convert to dictionary for backward compatibility."""
        return {key: table.to_dict() for key, table in self.tables.items()}

    @classmethod
    def from_dict(cls, data: dict[str, dict[str, Any]]) -> "MetadataCollection":
        """Create instance from dictionary."""
        tables = {}
        for key, table_data in data.items():
            tables[key] = TableMetadata.from_dict(table_data)
        return cls(tables=tables)
