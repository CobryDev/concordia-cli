"""
LookML Explore Module

This module generates LookML explores as Python dictionaries following the droughty pattern.
It handles explore definitions, joins between views, and explore-level configurations.
"""

from typing import List, Dict, Any, Optional
import click
from .field_utils import FieldIdentifier


class LookMLExploreGenerator:
    """Generates LookML explores as Python dictionaries."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the explore generator.

        Args:
            config: The loaded configuration dictionary
        """
        self.config = config
        self.model_rules = config['model_rules']
        self.looker_config = config['looker']
        self.field_identifier = FieldIdentifier(self.model_rules)

    def generate_explores_for_views(self, tables_metadata: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate explores for multiple views with automatic join detection.

        Args:
            tables_metadata: Dictionary of table metadata from MetadataExtractor

        Returns:
            List of explore dictionaries
        """
        explores = []

        # Generate individual explores for each table
        for table_key, table_metadata in tables_metadata.items():
            base_explore = self._generate_base_explore(table_metadata)
            explores.append(base_explore)

        # Generate explores with joins based on foreign key relationships
        joined_explores = self._generate_joined_explores(tables_metadata)
        explores.extend(joined_explores)

        return explores

    def _generate_base_explore(self, table_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a basic explore for a single view.

        Args:
            table_metadata: Table metadata dictionary

        Returns:
            Dictionary representing the LookML explore
        """
        view_name = self._get_view_name(table_metadata['table_id'])
        explore_name = self._get_explore_name(table_metadata['table_id'])

        explore_dict = {
            'explore': {
                explore_name: {
                    'from': view_name,
                    'view_name': view_name
                }
            }
        }

        # Add description if available
        if table_metadata.get('table_description'):
            explore_dict['explore'][explore_name][
                'description'] = f"Explore {table_metadata['table_description']}"

        # Add explore-level configurations
        explore_config = self.model_rules.get('explore_defaults', {})

        # Add default hidden fields
        if 'hidden' in explore_config:
            explore_dict['explore'][explore_name]['hidden'] = explore_config['hidden']

        # Add suggested fields for quick start
        suggested_fields = self._get_suggested_fields(table_metadata)
        if suggested_fields:
            explore_dict['explore'][explore_name]['fields'] = suggested_fields

        return explore_dict

    def _generate_joined_explores(self, tables_metadata: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate explores with joins based on foreign key relationships.

        Args:
            tables_metadata: Dictionary of table metadata

        Returns:
            List of explore dictionaries with joins
        """
        explores = []

        # Find potential join relationships
        join_relationships = self._detect_join_relationships(tables_metadata)

        for relationship in join_relationships:
            explore = self._create_joined_explore(
                relationship, tables_metadata)
            if explore:
                explores.append(explore)

        return explores

    def _detect_join_relationships(self, tables_metadata: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Detect potential join relationships between tables based on foreign keys.

        Args:
            tables_metadata: Dictionary of table metadata

        Returns:
            List of join relationship dictionaries
        """
        relationships = []

        for base_table_key, base_table in tables_metadata.items():
            for column in base_table['columns']:
                if self._is_foreign_key(column['name']):
                    # Try to find the referenced table
                    referenced_table = self._find_referenced_table(
                        column, tables_metadata)
                    if referenced_table:
                        relationships.append({
                            'base_table': base_table_key,
                            'base_table_metadata': base_table,
                            'join_table': referenced_table['table_key'],
                            'join_table_metadata': referenced_table['metadata'],
                            'join_column': column['name'],
                            'referenced_column': referenced_table['primary_key_column'],
                            'join_type': 'left_outer'  # Default join type
                        })

        return relationships

    def _find_referenced_table(self, foreign_key_column: Dict[str, Any],
                               tables_metadata: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Find the table referenced by a foreign key column.

        Args:
            foreign_key_column: Foreign key column metadata
            tables_metadata: Dictionary of table metadata

        Returns:
            Dictionary with referenced table information or None
        """
        fk_name = foreign_key_column['name']

        # Try to infer table name from foreign key name using configured suffixes
        # Example: user_fk -> users table, customer_fk -> customers table
        potential_table = self.field_identifier.infer_table_name_from_foreign_key(
            fk_name)
        if not potential_table:
            return None

        # Look for matching table
        for table_key, table_metadata in tables_metadata.items():
            table_id = table_metadata['table_id']
            if table_id == potential_table or table_id.endswith(f"_{potential_table}"):
                # Find primary key column in the referenced table
                pk_column = self._find_primary_key_column(table_metadata)
                if pk_column:
                    return {
                        'table_key': table_key,
                        'metadata': table_metadata,
                        'primary_key_column': pk_column
                    }

        return None

    def _find_primary_key_column(self, table_metadata: Dict[str, Any]) -> Optional[str]:
        """Find the primary key column in a table."""
        for column in table_metadata['columns']:
            if (column.get('is_primary_key') or
                self._is_primary_key(column['name']) or
                    column['name'] == 'id'):
                return column['name']
        return None

    def _create_joined_explore(self, relationship: Dict[str, Any],
                               tables_metadata: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Create an explore with joins based on a relationship.

        Args:
            relationship: Join relationship dictionary
            tables_metadata: Dictionary of table metadata

        Returns:
            Dictionary representing the joined explore
        """
        base_table = relationship['base_table_metadata']
        join_table = relationship['join_table_metadata']

        base_view_name = self._get_view_name(base_table['table_id'])
        join_view_name = self._get_view_name(join_table['table_id'])

        explore_name = f"{base_view_name}_with_{join_view_name}"

        explore_dict = {
            'explore': {
                explore_name: {
                    'from': base_view_name,
                    'view_name': base_view_name,
                    'join': [
                        {
                            join_view_name: {
                                'type': relationship['join_type'],
                                'sql_on': f"${{base_view_name}}.{relationship['join_column']} = ${{join_view_name}}.{relationship['referenced_column']}",
                                'relationship': 'many_to_one'
                            }
                        }
                    ]
                }
            }
        }

        # Add description
        explore_dict['explore'][explore_name][
            'description'] = f"Analysis of {base_table['table_id']} with {join_table['table_id']}"

        return explore_dict

    def generate_custom_explore(self, explore_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a custom explore based on configuration.

        Args:
            explore_config: Configuration dictionary for the explore

        Returns:
            Dictionary containing the explore definition
        """
        explore_name = explore_config['name']
        base_view = explore_config['base_view']

        explore_dict = {
            'explore': {
                explore_name: {
                    'from': base_view,
                    'view_name': base_view
                }
            }
        }

        # Add optional properties
        optional_props = ['description', 'hidden', 'label', 'group_label']
        for prop in optional_props:
            if prop in explore_config:
                explore_dict['explore'][explore_name][prop] = explore_config[prop]

        # Add custom joins
        if 'joins' in explore_config:
            explore_dict['explore'][explore_name]['join'] = []
            for join_config in explore_config['joins']:
                join_dict = self._create_custom_join(join_config)
                explore_dict['explore'][explore_name]['join'].append(join_dict)

        return explore_dict

    def _create_custom_join(self, join_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a custom join definition."""
        join_view = join_config['view']

        join_dict = {
            join_view: {
                'type': join_config.get('type', 'left_outer'),
                'sql_on': join_config['sql_on'],
                'relationship': join_config.get('relationship', 'many_to_one')
            }
        }

        # Add optional join properties
        optional_props = ['fields', 'foreign_key']
        for prop in optional_props:
            if prop in join_config:
                join_dict[join_view][prop] = join_config[prop]

        return join_dict

    def generate_aggregate_explore(self, base_explore: str, aggregation_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate an explore with aggregate tables or derived tables.

        Args:
            base_explore: Name of the base explore
            aggregation_config: Configuration for aggregation

        Returns:
            Dictionary containing the aggregate explore definition
        """
        explore_name = f"{base_explore}_aggregated"

        # Create derived table SQL for aggregation
        group_by_fields = aggregation_config.get('group_by', [])
        measures = aggregation_config.get('measures', [])

        derived_table_sql = self._build_aggregate_sql(
            base_explore, group_by_fields, measures)

        explore_dict = {
            'explore': {
                explore_name: {
                    'derived_table': {
                        'sql': derived_table_sql
                    },
                    'description': f"Aggregated view of {base_explore}"
                }
            }
        }

        return explore_dict

    def _build_aggregate_sql(self, base_explore: str, group_by_fields: List[str],
                             measures: List[str]) -> str:
        """Build SQL for aggregate derived table."""
        select_fields = group_by_fields + measures
        select_clause = ", ".join(select_fields)
        group_by_clause = ", ".join(group_by_fields) if group_by_fields else ""

        sql = f"""
        SELECT
          {select_clause}
        FROM ${{ref('{base_explore}')}}
        """

        if group_by_clause:
            sql += f"\nGROUP BY {group_by_clause}"

        return sql.strip()

    def _get_view_name(self, table_id: str) -> str:
        """Convert table ID to view name following naming conventions."""
        naming_rules = self.model_rules.get('naming_conventions', {})
        view_prefix = naming_rules.get('view_prefix', '')
        view_suffix = naming_rules.get('view_suffix', '')

        view_name = table_id.lower()

        if view_prefix:
            view_name = f"{view_prefix}{view_name}"
        if view_suffix:
            view_name = f"{view_name}{view_suffix}"

        return view_name

    def _get_explore_name(self, table_id: str) -> str:
        """Convert table ID to explore name following naming conventions."""
        naming_rules = self.model_rules.get('naming_conventions', {})
        explore_prefix = naming_rules.get('explore_prefix', '')
        explore_suffix = naming_rules.get('explore_suffix', '')

        explore_name = table_id.lower()

        if explore_prefix:
            explore_name = f"{explore_prefix}{explore_name}"
        if explore_suffix:
            explore_name = f"{explore_name}{explore_suffix}"

        return explore_name

    def _get_suggested_fields(self, table_metadata: Dict[str, Any]) -> List[str]:
        """Get suggested fields for quick explore setup."""
        suggested = []

        # Add primary key if available
        for column in table_metadata['columns']:
            if column.get('is_primary_key') or self._is_primary_key(column['name']):
                suggested.append(column['name'])
                break

        # Add first few non-hidden string fields
        string_fields = [col['name'] for col in table_metadata['columns']
                         if col['type'] == 'STRING' and not self._should_hide_field(col['name'])]
        suggested.extend(string_fields[:3])

        # Add timestamp fields
        time_fields = [col['name'] for col in table_metadata['columns']
                       if col['type'] in ['TIMESTAMP', 'DATETIME', 'DATE']]
        suggested.extend(time_fields[:2])

        return suggested[:6]  # Limit to 6 suggested fields

    def _is_foreign_key(self, field_name: str) -> bool:
        """Check if a field is a foreign key based on naming conventions."""
        return self.field_identifier.is_foreign_key(field_name)

    def _is_primary_key(self, field_name: str) -> bool:
        """Check if a field is a primary key based on naming conventions."""
        return self.field_identifier.is_primary_key(field_name)

    def _should_hide_field(self, field_name: str) -> bool:
        """Check if a field should be hidden based on configuration."""
        return self.field_identifier.should_hide_field(field_name)
