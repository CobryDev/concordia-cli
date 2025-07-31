"""
LookML Module

This module creates LookML views as Python dictionaries following the droughty pattern.
It handles dimensions, dimension groups, and view-level configurations.
"""

from typing import List, Dict, Any, Optional
import click
from .field_utils import FieldIdentifier


class LookMLViewGenerator:
    """Generates LookML views as Python dictionaries."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the view generator.

        Args:
            config: The loaded configuration dictionary
        """
        self.config = config
        self.model_rules = config['model_rules']
        self.looker_config = config['looker']
        self.connection_name = self.looker_config['connection']
        self.field_identifier = FieldIdentifier(self.model_rules)

    def generate_view_dict(self, table_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a LookML view dictionary for a table.

        Args:
            table_metadata: Table metadata dictionary from MetadataExtractor

        Returns:
            Dictionary representing the LookML view
        """
        view_name = self._get_view_name(table_metadata['table_id'])

        # Build the view dictionary structure
        view_dict = {
            'view': {
                view_name: {
                    'sql_table_name': f"`{table_metadata['project_id']}.{table_metadata['dataset_id']}.{table_metadata['table_id']}`",
                    'connection': self.connection_name
                }
            }
        }

        # Add description if available
        if table_metadata.get('table_description'):
            view_dict['view'][view_name]['description'] = table_metadata['table_description']

        # Generate dimensions and dimension groups
        dimensions = []
        dimension_groups = []
        drill_fields = []

        for column in table_metadata['columns']:
            if self._is_time_dimension(column):
                dimension_group = self._generate_dimension_group(column)
                if dimension_group:
                    dimension_groups.append(dimension_group)
            else:
                dimension = self._generate_dimension(column)
                if dimension:
                    dimensions.append(dimension)

                    # Add to drill fields if not hidden
                    if not self._should_hide_field(column['name']):
                        drill_fields.append(column['name'])

        # Add dimensions to view
        if dimensions:
            if 'dimension' not in view_dict['view'][view_name]:
                view_dict['view'][view_name]['dimension'] = []
            view_dict['view'][view_name]['dimension'].extend(dimensions)

        # Add dimension groups to view
        if dimension_groups:
            if 'dimension_group' not in view_dict['view'][view_name]:
                view_dict['view'][view_name]['dimension_group'] = []
            view_dict['view'][view_name]['dimension_group'].extend(
                dimension_groups)

        # Add drill fields set
        if drill_fields:
            view_dict['view'][view_name]['set'] = {
                'detail': {
                    'fields': drill_fields
                }
            }

        return view_dict

    def _get_view_name(self, table_id: str) -> str:
        """Convert table ID to view name following naming conventions."""
        # Apply any naming transformations based on config
        naming_rules = self.model_rules.get('naming_conventions', {})
        view_prefix = naming_rules.get('view_prefix', '')
        view_suffix = naming_rules.get('view_suffix', '')

        view_name = table_id.lower()

        if view_prefix:
            view_name = f"{view_prefix}{view_name}"
        if view_suffix:
            view_name = f"{view_name}{view_suffix}"

        return view_name

    def _generate_dimension(self, column: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Generate a LookML dimension dictionary for a column.

        Args:
            column: Column metadata dictionary

        Returns:
            Dictionary containing dimension definition or None if unsupported
        """
        column_name = column['name']
        standardized_type = column['standardized_type']

        # Find type mapping from config
        type_mapping = self._find_type_mapping(column['type'])
        if not type_mapping:
            click.echo(
                f"   ⚠️  No type mapping found for BigQuery type '{column['type']}' in column '{column_name}'")
            return None

        dimension_dict = {
            column_name: {
                'type': type_mapping['lookml_type'],
                'sql': f"${{TABLE}}.{column_name}"
            }
        }

        # Add description if available
        if column.get('description'):
            dimension_dict[column_name]['description'] = column['description']

        # Add type-specific parameters
        lookml_params = type_mapping.get('lookml_params', {})
        for param, value in lookml_params.items():
            if param != 'sql':  # sql is handled above
                dimension_dict[column_name][param] = value

        # Handle primary key
        if column.get('is_primary_key') or self._is_primary_key(column_name):
            dimension_dict[column_name]['primary_key'] = 'yes'

        # Handle hidden fields
        if self._should_hide_field(column_name):
            dimension_dict[column_name]['hidden'] = 'yes'

        return dimension_dict

    def _generate_dimension_group(self, column: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Generate a LookML dimension group dictionary for time-based columns.

        Args:
            column: Column metadata dictionary

        Returns:
            Dictionary containing dimension group definition
        """
        column_name = column['name']
        column_type = column['type']

        # Determine timeframes based on column type
        if column_type in ['TIMESTAMP', 'DATETIME']:
            timeframes = ['raw', 'time', 'date',
                          'week', 'month', 'quarter', 'year']
            dimension_type = 'time'
        elif column_type == 'DATE':
            timeframes = ['raw', 'date', 'week', 'month', 'quarter', 'year']
            dimension_type = 'time'
        else:
            return None

        # Remove suffix if it's a timestamp field
        group_name = column_name
        if group_name.endswith(('_at', '_date', '_time', '_ts', '_timestamp')):
            group_name = group_name.rsplit('_', 1)[0]

        dimension_group_dict = {
            group_name: {
                'type': dimension_type,
                'timeframes': timeframes,
                'sql': f"${{TABLE}}.{column_name}"
            }
        }

        # Add description if available
        if column.get('description'):
            dimension_group_dict[group_name]['description'] = column['description']

        # Handle hidden fields
        if self._should_hide_field(column_name):
            dimension_group_dict[group_name]['hidden'] = 'yes'

        return dimension_group_dict

    def _is_time_dimension(self, column: Dict[str, Any]) -> bool:
        """Check if a column should be treated as a time dimension group."""
        time_types = ['TIMESTAMP', 'DATETIME', 'DATE', 'TIME']
        return column['type'] in time_types

    def _find_type_mapping(self, bq_type: str) -> Optional[Dict[str, Any]]:
        """Find the LookML type mapping for a BigQuery type."""
        for mapping in self.model_rules['type_mapping']:
            if mapping['bq_type'] == bq_type:
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

    def __init__(self, config: Dict[str, Any]):
        """Initialize with configuration."""
        self.config = config
        self.model_rules = config['model_rules']

    def generate_case_dimension(self, column: Dict[str, Any], case_logic: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a case-based dimension with conditional logic.

        Args:
            column: Column metadata dictionary
            case_logic: Dictionary defining case conditions

        Returns:
            Dictionary containing case dimension definition
        """
        column_name = column['name']
        case_name = case_logic.get('name', f"{column_name}_category")

        case_sql_parts = []
        for condition in case_logic['conditions']:
            case_sql_parts.append(
                f"WHEN {condition['condition']} THEN '{condition['value']}'")

        default_value = case_logic.get('default', 'Other')
        sql = f"CASE {' '.join(case_sql_parts)} ELSE '{default_value}' END"

        return {
            case_name: {
                'type': 'string',
                'sql': sql,
                'description': case_logic.get('description', f"Categorized {column_name}")
            }
        }

    def generate_yesno_dimension(self, column: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a yes/no dimension from a boolean or numeric column.

        Args:
            column: Column metadata dictionary

        Returns:
            Dictionary containing yes/no dimension definition
        """
        column_name = column['name']

        if column['type'] == 'BOOLEAN':
            sql = f"${{TABLE}}.{column_name}"
        else:
            # Assume numeric where > 0 means yes
            sql = f"${{TABLE}}.{column_name} > 0"

        return {
            column_name: {
                'type': 'yesno',
                'sql': sql,
                'description': column.get('description', f"Yes/No indicator for {column_name}")
            }
        }
