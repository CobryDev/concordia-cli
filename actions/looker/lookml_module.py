"""
LookML Module

This module creates LookML views as Python dictionaries following the droughty pattern.
It handles dimensions, dimension groups, and view-level configurations.
"""

from typing import Any, Optional

import click

from ..models.config import ConcordiaConfig, TypeMapping
from ..models.lookml import Dimension, DimensionGroup, DimensionGroupType, DimensionType, LookMLView
from ..models.metadata import ColumnMetadata, TableMetadata
from .field_utils import FieldIdentifier
from ..utils.lookml_naming import LookMLNameValidator


class LookMLViewGenerator:
    """Generates LookML views as Python dictionaries."""

    def __init__(self, config: ConcordiaConfig):
        """
        Initialize the view generator.

        Args:
            config: The loaded ConcordiaConfig object
        """
        self.config = config
        self.model_rules = config.model_rules
        self.looker_config = config.looker
        self.connection_name = self.looker_config.connection
        self.field_identifier = FieldIdentifier(self.model_rules)
        self.name_validator = LookMLNameValidator(self.model_rules.naming_conventions.character_replacements)

    def generate_view_dict(self, table_metadata: TableMetadata) -> dict[str, Any]:
        """
        Generate a LookML view dictionary for a table.

        Args:
            table_metadata: Table metadata dictionary from MetadataExtractor

        Returns:
            Dictionary representing the LookML view
        """
        view_name = self._get_view_name(table_metadata.table_id)

        # Build the view dictionary structure (omit connection and view-level description)
        view_dict = {
            "view": {
                view_name: {
                    "sql_table_name": f"`{table_metadata.project_id}."
                    f"{table_metadata.dataset_id}.{table_metadata.table_id}`"
                }
            }
        }

        # Generate dimensions and dimension groups
        dimensions = []
        dimension_groups = []
        drill_fields = []
        dimension_group_names: set[str] = set()

        for column in table_metadata.columns:
            if self._is_time_dimension(column):
                dimension_group = self._generate_dimension_group(column)
                if dimension_group:
                    group_name = next(iter(dimension_group))
                    resolved_name = self._resolve_dimension_group_name(
                        base_name=group_name, column=column, existing_names=dimension_group_names
                    )

                    # Rename the dimension group key if we had to resolve a conflict
                    if resolved_name != group_name:
                        dimension_group = {resolved_name: dimension_group[group_name]}

                    dimension_groups.append(dimension_group)
                    dimension_group_names.add(resolved_name)
            else:
                dimension = self._generate_dimension(column)
                if dimension:
                    dimensions.append(dimension)

                    # Add to drill fields if not hidden
                    if not self._should_hide_field(column.name):
                        dimension_name = next(iter(dimension))
                        drill_fields.append(dimension_name)

        # Add dimensions to view (using type: ignore to suppress type checker warnings)
        if dimensions:
            view_content = view_dict["view"][view_name]
            if "dimension" not in view_content:
                view_content["dimension"] = []  # type: ignore
            view_content["dimension"].extend(dimensions)  # type: ignore

        # Add dimension groups to view (using type: ignore to suppress type checker warnings)
        if dimension_groups:
            view_content = view_dict["view"][view_name]
            if "dimension_group" not in view_content:
                view_content["dimension_group"] = []  # type: ignore
            # type: ignore
            dimension_group_list = view_content["dimension_group"]
            dimension_group_list.extend(dimension_groups)  # type: ignore

        # Add drill fields set (using type: ignore to suppress type checker warnings)
        if drill_fields:
            # Use explicit name form so lkml serializes as: set: all_fields { ... }
            view_dict["view"][view_name]["set"] = {  # type: ignore
                "name": "all_fields",
                "fields": drill_fields,
            }

        return view_dict

    def _get_view_name(self, table_id: str) -> str:
        """Convert table ID to view name following naming conventions."""
        # Apply any naming transformations based on config
        naming_rules = self.model_rules.naming_conventions
        view_prefix = naming_rules.view_prefix or ""
        view_suffix = naming_rules.view_suffix or ""

        view_name = table_id.lower()

        if view_prefix:
            view_name = f"{view_prefix}{view_name}"
        if view_suffix:
            view_name = f"{view_name}{view_suffix}"

        return self.name_validator.sanitize(view_name, "view")

    def _generate_dimension(self, column: ColumnMetadata) -> Optional[dict[str, Any]]:
        """
        Generate a LookML dimension dictionary for a column.

        Args:
            column: ColumnMetadata object

        Returns:
            Dictionary containing dimension definition or None if unsupported
        """
        column_name = column.name
        dimension_name = self.name_validator.sanitize(column_name, "dimension")

        # Find type mapping from config
        type_mapping = self._find_type_mapping(column.type)
        if not type_mapping:
            click.echo(f"   ⚠️  No type mapping found for BigQuery type '{column.type}' in column '{column_name}'")
            return None

        dimension_dict = {
            dimension_name: {
                "type": type_mapping.lookml_type,
                "sql": f"${{TABLE}}.{column_name}",
            }
        }

        # Add description if available
        if column.description:
            dimension_dict[dimension_name]["description"] = column.description

        # Add type-specific parameters
        if hasattr(type_mapping, "lookml_params") and type_mapping.lookml_params:
            # Convert Pydantic model to dict for iteration
            if hasattr(type_mapping.lookml_params, "model_dump"):
                lookml_params_dict = type_mapping.lookml_params.model_dump()
            elif hasattr(type_mapping.lookml_params, "dict"):
                lookml_params_dict = type_mapping.lookml_params.dict()
            elif isinstance(type_mapping.lookml_params, dict):
                # It's already a dictionary
                lookml_params_dict = type_mapping.lookml_params
            else:
                # Skip if we can't convert to dict (might be a Pydantic model we can't handle)
                lookml_params_dict = None

            if lookml_params_dict:
                for param, value in lookml_params_dict.items():
                    if param != "sql":  # sql is handled above
                        dimension_dict[dimension_name][param] = value

        # Handle primary key
        if getattr(column, "is_primary_key", False) or self._is_primary_key(column_name):
            dimension_dict[dimension_name]["primary_key"] = "yes"

        # Handle hidden fields
        if self._should_hide_field(column_name):
            dimension_dict[dimension_name]["hidden"] = "yes"

        return dimension_dict

    def _generate_dimension_group(self, column: ColumnMetadata) -> Optional[dict[str, Any]]:
        """
        Generate a LookML dimension group dictionary for time-based columns.

        Args:
            column: ColumnMetadata object

        Returns:
            Dictionary containing dimension group definition
        """
        column_name = column.name
        column_type = column.type

        # Determine timeframes based on column type
        if column_type in ["TIMESTAMP", "DATETIME"]:
            timeframes = ["raw", "time", "date", "week", "month", "quarter", "year"]
            dimension_type = "time"
        elif column_type == "DATE":
            timeframes = ["raw", "date", "week", "month", "quarter", "year"]
            dimension_type = "time"
        else:
            return None

        # Remove suffix if it's a timestamp field
        group_name = column_name
        if group_name.endswith(("_at", "_date", "_time", "_ts", "_timestamp")):
            group_name = group_name.rsplit("_", 1)[0]

        group_name = self.name_validator.sanitize(group_name, "dimension group")

        dimension_group_dict = {
            group_name: {
                "type": dimension_type,
                "timeframes": timeframes,
                "sql": f"${{TABLE}}.{column_name}",
            }
        }

        # Add description if available
        if column.description:
            dimension_group_dict[group_name]["description"] = column.description

        # Handle hidden fields
        if self._should_hide_field(column_name):
            dimension_group_dict[group_name]["hidden"] = "yes"

        return dimension_group_dict

    def _resolve_dimension_group_name(self, base_name: str, column: ColumnMetadata, existing_names: set[str]) -> str:
        """
        Ensure dimension group names remain unique by applying type-specific suffixes when needed.

        Args:
            base_name: The initial dimension group name (after suffix stripping)
            column: Column metadata used to infer suffixes and fallbacks
            existing_names: Set of dimension group names already in use

        Returns:
            A unique dimension group name
        """
        if base_name not in existing_names:
            return base_name

        suffix = self._time_dimension_suffix(column.type)
        candidates = []

        if suffix:
            candidates.append(self.name_validator.sanitize(f"{base_name}{suffix}", "dimension group"))

        # Fall back to the raw column name if suffix-based name still collides
        candidates.append(self.name_validator.sanitize(column.name, "dimension group"))

        for candidate in candidates:
            if candidate not in existing_names:
                return candidate

        # Final fallback: numeric suffix to guarantee uniqueness
        counter = 2
        while True:
            candidate = self.name_validator.sanitize(f"{base_name}_{counter}", "dimension group")
            if candidate not in existing_names:
                return candidate
            counter += 1

    def _time_dimension_suffix(self, column_type: str) -> str:
        """Return a suffix to use for time dimension groups based on column type."""
        suffix_map = {
            "TIMESTAMP": "_at",
            "DATETIME": "_at",
            "TIME": "_at",
            "DATE": "_on",
        }

        if not column_type:
            return ""

        return suffix_map.get(column_type.upper(), "")

    def _is_time_dimension(self, column: ColumnMetadata) -> bool:
        """Check if a column should be treated as a time dimension group."""
        time_types = ["TIMESTAMP", "DATETIME", "DATE", "TIME"]
        return column.type in time_types

    def _find_type_mapping(self, bq_type: str) -> Optional[TypeMapping]:
        """Find the LookML type mapping for a BigQuery type."""
        for mapping in self.model_rules.type_mapping:
            if mapping.bq_type == bq_type:
                return mapping
        return None

    def _should_hide_field(self, field_name: str) -> bool:
        """Check if a field should be hidden based on configuration."""
        return self.field_identifier.should_hide_field(field_name)

    def _is_primary_key(self, field_name: str) -> bool:
        """Check if a field is a primary key based on naming conventions."""
        return self.field_identifier.is_primary_key(field_name)

    def _is_foreign_key(self, field_name: str) -> bool:
        """Check if a field is a foreign key based on naming conventions."""
        return self.field_identifier.is_foreign_key(field_name)


class LookMLDimensionGenerator:
    """Specialized generator for complex dimension types."""

    def __init__(self, config: ConcordiaConfig):
        """Initialize with configuration."""
        self.config = config
        self.model_rules = config.model_rules
        self.looker_config = config.looker
        self.connection_name = self.looker_config.connection
        self.field_identifier = FieldIdentifier(self.model_rules)
        self.name_validator = LookMLNameValidator(self.model_rules.naming_conventions.character_replacements)

    def generate_case_dimension(self, column: ColumnMetadata, case_logic: dict[str, Any]) -> dict[str, Any]:
        """
        Generate a case-based dimension with conditional logic.

        Args:
            column: ColumnMetadata object
            case_logic: Dictionary defining case conditions

        Returns:
            Dictionary containing case dimension definition
        """
        column_name = column.name
        case_name = case_logic.get("name", f"{column_name}_category")

        case_sql_parts = []
        for condition in case_logic["conditions"]:
            case_sql_parts.append(f"WHEN {condition['condition']} THEN '{condition['value']}'")

        default_value = case_logic.get("default", "Other")
        sql = f"CASE {' '.join(case_sql_parts)} ELSE '{default_value}' END"

        return {
            case_name: {
                "type": "string",
                "sql": sql,
                "description": case_logic.get("description", f"Categorized {column_name}"),
            }
        }

    def generate_yesno_dimension(self, column: ColumnMetadata) -> dict[str, Any]:
        """
        Generate a yes/no dimension from a boolean or numeric column.

        Args:
            column: ColumnMetadata object

        Returns:
            Dictionary containing yes/no dimension definition
        """
        column_name = column.name

        if column.type == "BOOLEAN":
            sql = f"${{TABLE}}.{column_name}"
        else:
            # Assume numeric where > 0 means yes
            sql = f"${{TABLE}}.{column_name} > 0"

        description = column.description if column.description else f"Yes/No indicator for {column_name}"

        return {column_name: {"type": "yesno", "sql": sql, "description": description}}

    def generate_lookml_view(self, table_metadata: TableMetadata) -> LookMLView:
        """
        Generate a LookMLView object for a table using Pydantic models.

        Args:
            table_metadata: TableMetadata object from MetadataExtractor

        Returns:
            LookMLView object representing the view
        """
        view_name = self._get_view_name(table_metadata.table_id)

        # Create the base view (omit connection and view-level description)
        lookml_view = LookMLView(
            name=view_name,
            sql_table_name=f"`{table_metadata.project_id}.{table_metadata.dataset_id}.{table_metadata.table_id}`",
        )

        # Generate dimensions and dimension groups
        for column in table_metadata.columns:
            if self._is_time_dimension_pydantic(column):
                dimension_group = self._generate_dimension_group_pydantic(column)
                if dimension_group:
                    lookml_view.add_dimension_group(dimension_group)
            else:
                dimension = self._generate_dimension_pydantic(column)
                if dimension:
                    lookml_view.add_dimension(dimension)

        return lookml_view

    def _is_time_dimension_pydantic(self, column: ColumnMetadata) -> bool:
        """Check if column should be treated as a time dimension."""
        return column.is_time_type()

    def _generate_dimension_pydantic(self, column: ColumnMetadata) -> Optional[Dimension]:
        """Generate a Dimension object from column metadata."""
        if self._should_hide_field(column.name):
            return None

        # Determine dimension type
        if column.is_boolean_type():
            dim_type = DimensionType.YESNO
        elif column.is_numeric_type():
            dim_type = DimensionType.NUMBER
        else:
            dim_type = DimensionType.STRING

        return Dimension(
            name=self.name_validator.sanitize(column.name, "dimension"),
            type=dim_type,
            sql=f"${{TABLE}}.{column.name}",
            description=column.description,
            primary_key=column.is_primary_key,
            hidden=self._should_hide_field(column.name),
        )

    def _generate_dimension_group_pydantic(self, column: ColumnMetadata) -> Optional[DimensionGroup]:
        """Generate a DimensionGroup object from time column metadata."""
        if column.standardized_type == "TIMESTAMP":
            timeframes = ["raw", "time", "date", "week", "month", "quarter", "year"]
        elif column.standardized_type == "DATE":
            timeframes = ["date", "week", "month", "quarter", "year"]
        else:
            timeframes = ["raw", "date"]

        return DimensionGroup(
            name=self.name_validator.sanitize(column.name, "dimension group"),
            type=DimensionGroupType.TIME,
            sql=f"${{TABLE}}.{column.name}",
            description=column.description,
            timeframes=timeframes,
        )

    def _get_view_name(self, table_id: str) -> str:
        """Convert table ID to view name following naming conventions."""
        # Apply any naming transformations based on config
        naming_rules = self.model_rules.naming_conventions
        view_prefix = naming_rules.view_prefix or ""
        view_suffix = naming_rules.view_suffix or ""

        view_name = table_id.lower()

        if view_prefix:
            view_name = f"{view_prefix}{view_name}"
        if view_suffix:
            view_name = f"{view_name}{view_suffix}"

        return self.name_validator.sanitize(view_name, "view")

    def _should_hide_field(self, field_name: str) -> bool:
        """Check if a field should be hidden based on configuration."""
        return self.field_identifier.should_hide_field(field_name)
