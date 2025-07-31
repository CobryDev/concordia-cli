"""
Unit tests for lookml_explore_module.py.

Tests the LookMLExploreGenerator class for explore generation,
join logic, and relationship detection.
"""

import pytest
from actions.looker.lookml_explore_module import LookMLExploreGenerator
from tests.fixtures.config_fixtures import (
    sample_config, sample_model_rules, sample_table_metadata,
    sample_multiple_tables_metadata
)


class TestLookMLExploreGenerator:
    """Test cases for LookMLExploreGenerator class."""

    def test_init(self, sample_config):
        """Test initialization of LookMLExploreGenerator."""
        generator = LookMLExploreGenerator(sample_config)

        assert generator.config == sample_config
        assert generator.model_rules == sample_config['model_rules']
        assert generator.looker_config == sample_config['looker']
        assert generator.field_identifier is not None

    def test_generate_explores_for_views_single_table(self, sample_config, sample_multiple_tables_metadata):
        """Test explore generation for single table."""
        generator = LookMLExploreGenerator(sample_config)

        # Test with single table
        single_table = {
            'test_dataset.users': sample_multiple_tables_metadata['test_dataset.users']}
        explores = generator.generate_explores_for_views(single_table)

        assert len(explores) >= 1  # At least one base explore

        # Check base explore exists
        explore_names = []
        for explore in explores:
            if 'explore' in explore:
                explore_names.extend(explore['explore'].keys())

        assert 'users' in explore_names

    def test_generate_explores_for_views_multiple_tables(self, sample_config, sample_multiple_tables_metadata):
        """Test explore generation for multiple tables with joins."""
        generator = LookMLExploreGenerator(sample_config)
        explores = generator.generate_explores_for_views(
            sample_multiple_tables_metadata)

        # Should have base explores for each table plus potential joined explores
        # At least base explores for users and organizations
        assert len(explores) >= 2

        explore_names = []
        for explore in explores:
            if 'explore' in explore:
                explore_names.extend(explore['explore'].keys())

        assert 'users' in explore_names
        assert 'organizations' in explore_names

    def test_generate_base_explore_basic_structure(self, sample_config, sample_table_metadata):
        """Test basic explore structure generation."""
        generator = LookMLExploreGenerator(sample_config)
        result = generator._generate_base_explore(sample_table_metadata)

        assert 'explore' in result
        assert 'users' in result['explore']

        explore = result['explore']['users']
        assert explore['from'] == 'users'
        assert explore['view_name'] == 'users'
        assert explore['description'] == 'Explore User information table'

    def test_generate_base_explore_without_description(self, sample_config, sample_table_metadata):
        """Test base explore generation when table has no description."""
        # Remove description
        table_metadata = sample_table_metadata.copy()
        del table_metadata['table_description']

        generator = LookMLExploreGenerator(sample_config)
        result = generator._generate_base_explore(table_metadata)

        explore = result['explore']['users']
        assert 'description' not in explore

    def test_generate_base_explore_with_suggested_fields(self, sample_config, sample_table_metadata):
        """Test base explore generation includes suggested fields."""
        generator = LookMLExploreGenerator(sample_config)
        result = generator._generate_base_explore(sample_table_metadata)

        explore = result['explore']['users']
        assert 'fields' in explore
        assert isinstance(explore['fields'], list)
        assert len(explore['fields']) > 0

    def test_detect_join_relationships_with_foreign_keys(self, sample_config, sample_multiple_tables_metadata):
        """Test detection of join relationships based on foreign keys."""
        generator = LookMLExploreGenerator(sample_config)
        relationships = generator._detect_join_relationships(
            sample_multiple_tables_metadata)

        # Should detect relationship between users.organization_fk and organizations.organization_pk
        assert len(relationships) >= 1

        # Check the detected relationship
        user_org_relationship = next(
            (r for r in relationships
             if r['base_table'] == 'test_dataset.users' and r['join_column'] == 'organization_fk'),
            None
        )

        assert user_org_relationship is not None
        assert user_org_relationship['join_table'] == 'test_dataset.organizations'
        assert user_org_relationship['referenced_column'] == 'organization_pk'
        assert user_org_relationship['join_type'] == 'left_outer'

    def test_detect_join_relationships_no_foreign_keys(self, sample_config):
        """Test relationship detection when no foreign keys exist."""
        generator = LookMLExploreGenerator(sample_config)

        # Create tables without foreign keys
        tables_without_fks = {
            'test_dataset.table1': {
                'table_id': 'table1',
                'columns': [
                    {'name': 'id', 'type': 'INTEGER'},
                    {'name': 'name', 'type': 'STRING'}
                ]
            },
            'test_dataset.table2': {
                'table_id': 'table2',
                'columns': [
                    {'name': 'id', 'type': 'INTEGER'},
                    {'name': 'value', 'type': 'STRING'}
                ]
            }
        }

        relationships = generator._detect_join_relationships(
            tables_without_fks)
        assert len(relationships) == 0

    def test_find_referenced_table_successful_match(self, sample_config, sample_multiple_tables_metadata):
        """Test finding referenced table from foreign key."""
        generator = LookMLExploreGenerator(sample_config)

        foreign_key_column = {
            'name': 'organization_fk',
            'type': 'INTEGER'
        }

        result = generator._find_referenced_table(
            foreign_key_column, sample_multiple_tables_metadata)

        assert result is not None
        assert result['table_key'] == 'test_dataset.organizations'
        assert result['primary_key_column'] == 'organization_pk'

    def test_find_referenced_table_no_match(self, sample_config, sample_multiple_tables_metadata):
        """Test finding referenced table when no match exists."""
        generator = LookMLExploreGenerator(sample_config)

        foreign_key_column = {
            'name': 'nonexistent_fk',
            'type': 'INTEGER'
        }

        result = generator._find_referenced_table(
            foreign_key_column, sample_multiple_tables_metadata)
        assert result is None

    def test_find_primary_key_column_explicit_pk(self, sample_config):
        """Test finding primary key column when explicitly marked."""
        generator = LookMLExploreGenerator(sample_config)

        table_metadata = {
            'columns': [
                {'name': 'user_pk', 'type': 'INTEGER', 'is_primary_key': True},
                {'name': 'email', 'type': 'STRING'}
            ]
        }

        pk_column = generator._find_primary_key_column(table_metadata)
        assert pk_column == 'user_pk'

    def test_find_primary_key_column_by_naming_convention(self, sample_config):
        """Test finding primary key column by naming convention."""
        generator = LookMLExploreGenerator(sample_config)

        table_metadata = {
            'columns': [
                {'name': 'user_pk', 'type': 'INTEGER'},
                {'name': 'email', 'type': 'STRING'}
            ]
        }

        pk_column = generator._find_primary_key_column(table_metadata)
        assert pk_column == 'user_pk'

    def test_find_primary_key_column_id_field(self, sample_config):
        """Test finding primary key column when named 'id'."""
        generator = LookMLExploreGenerator(sample_config)

        table_metadata = {
            'columns': [
                {'name': 'id', 'type': 'INTEGER'},
                {'name': 'email', 'type': 'STRING'}
            ]
        }

        pk_column = generator._find_primary_key_column(table_metadata)
        assert pk_column == 'id'

    def test_find_primary_key_column_not_found(self, sample_config):
        """Test finding primary key column when none exists."""
        generator = LookMLExploreGenerator(sample_config)

        table_metadata = {
            'columns': [
                {'name': 'email', 'type': 'STRING'},
                {'name': 'name', 'type': 'STRING'}
            ]
        }

        pk_column = generator._find_primary_key_column(table_metadata)
        assert pk_column is None

    def test_create_joined_explore(self, sample_config, sample_multiple_tables_metadata):
        """Test creation of joined explore."""
        generator = LookMLExploreGenerator(sample_config)

        relationship = {
            'base_table_metadata': sample_multiple_tables_metadata['test_dataset.users'],
            'join_table_metadata': sample_multiple_tables_metadata['test_dataset.organizations'],
            'join_column': 'organization_fk',
            'referenced_column': 'organization_pk',
            'join_type': 'left_outer'
        }

        result = generator._create_joined_explore(
            relationship, sample_multiple_tables_metadata)

        assert result is not None
        assert 'explore' in result
        assert 'users_with_organizations' in result['explore']

        explore = result['explore']['users_with_organizations']
        assert explore['from'] == 'users'
        assert explore['view_name'] == 'users'
        assert 'join' in explore
        assert len(explore['join']) == 1

        join = explore['join'][0]['organizations']
        assert join['type'] == 'left_outer'
        assert 'organization_fk' in join['sql_on']
        assert 'organization_pk' in join['sql_on']
        assert join['relationship'] == 'many_to_one'

    def test_generate_custom_explore_basic(self, sample_config):
        """Test custom explore generation with basic configuration."""
        generator = LookMLExploreGenerator(sample_config)

        explore_config = {
            'name': 'custom_analysis',
            'base_view': 'users',
            'description': 'Custom user analysis'
        }

        result = generator.generate_custom_explore(explore_config)

        assert 'explore' in result
        assert 'custom_analysis' in result['explore']

        explore = result['explore']['custom_analysis']
        assert explore['from'] == 'users'
        assert explore['view_name'] == 'users'
        assert explore['description'] == 'Custom user analysis'

    def test_generate_custom_explore_with_joins(self, sample_config):
        """Test custom explore generation with joins."""
        generator = LookMLExploreGenerator(sample_config)

        explore_config = {
            'name': 'users_with_orders',
            'base_view': 'users',
            'joins': [
                {
                    'view': 'orders',
                    'type': 'inner',
                    'sql_on': '${users.user_pk} = ${orders.user_fk}',
                    'relationship': 'one_to_many'
                }
            ]
        }

        result = generator.generate_custom_explore(explore_config)

        explore = result['explore']['users_with_orders']
        assert 'join' in explore
        assert len(explore['join']) == 1

        join = explore['join'][0]['orders']
        assert join['type'] == 'inner'
        assert join['relationship'] == 'one_to_many'

    def test_create_custom_join(self, sample_config):
        """Test custom join creation."""
        generator = LookMLExploreGenerator(sample_config)

        join_config = {
            'view': 'orders',
            'type': 'inner',
            'sql_on': '${users.id} = ${orders.user_id}',
            'relationship': 'one_to_many',
            'fields': ['order_date', 'amount']
        }

        result = generator._create_custom_join(join_config)

        assert 'orders' in result
        join = result['orders']
        assert join['type'] == 'inner'
        assert join['sql_on'] == '${users.id} = ${orders.user_id}'
        assert join['relationship'] == 'one_to_many'
        assert join['fields'] == ['order_date', 'amount']

    def test_create_custom_join_with_defaults(self, sample_config):
        """Test custom join creation with default values."""
        generator = LookMLExploreGenerator(sample_config)

        join_config = {
            'view': 'orders',
            'sql_on': '${users.id} = ${orders.user_id}'
        }

        result = generator._create_custom_join(join_config)

        join = result['orders']
        assert join['type'] == 'left_outer'  # Default
        assert join['relationship'] == 'many_to_one'  # Default

    def test_generate_aggregate_explore(self, sample_config):
        """Test aggregate explore generation."""
        generator = LookMLExploreGenerator(sample_config)

        aggregation_config = {
            'group_by': ['region', 'product_category'],
            'measures': ['SUM(revenue)', 'COUNT(*)']
        }

        result = generator.generate_aggregate_explore(
            'orders', aggregation_config)

        assert 'explore' in result
        assert 'orders_aggregated' in result['explore']

        explore = result['explore']['orders_aggregated']
        assert 'derived_table' in explore
        assert 'sql' in explore['derived_table']

        sql = explore['derived_table']['sql']
        assert 'SELECT' in sql
        assert 'region' in sql
        assert 'product_category' in sql
        assert 'GROUP BY' in sql

    def test_build_aggregate_sql_with_group_by(self, sample_config):
        """Test aggregate SQL building with GROUP BY."""
        generator = LookMLExploreGenerator(sample_config)

        sql = generator._build_aggregate_sql(
            'orders',
            ['region', 'category'],
            ['SUM(amount)', 'COUNT(*)']
        )

        assert 'SELECT' in sql
        assert 'region, category, SUM(amount), COUNT(*)' in sql
        assert 'FROM ${ref(\'orders\')}' in sql
        assert 'GROUP BY region, category' in sql

    def test_build_aggregate_sql_without_group_by(self, sample_config):
        """Test aggregate SQL building without GROUP BY."""
        generator = LookMLExploreGenerator(sample_config)

        sql = generator._build_aggregate_sql(
            'orders',
            [],
            ['SUM(amount)', 'COUNT(*)']
        )

        assert 'SELECT' in sql
        assert 'SUM(amount), COUNT(*)' in sql
        assert 'GROUP BY' not in sql

    def test_get_view_name_default(self, sample_config):
        """Test view name generation with default settings."""
        generator = LookMLExploreGenerator(sample_config)

        assert generator._get_view_name('Users') == 'users'
        assert generator._get_view_name('ORDER_ITEMS') == 'order_items'

    def test_get_view_name_with_prefix_suffix(self, sample_config):
        """Test view name generation with prefix and suffix."""
        sample_config['model_rules']['naming_conventions']['view_prefix'] = 'vw_'
        sample_config['model_rules']['naming_conventions']['view_suffix'] = '_view'

        generator = LookMLExploreGenerator(sample_config)

        assert generator._get_view_name('users') == 'vw_users_view'

    def test_get_explore_name_default(self, sample_config):
        """Test explore name generation with default settings."""
        generator = LookMLExploreGenerator(sample_config)

        assert generator._get_explore_name('Users') == 'users'
        assert generator._get_explore_name('ORDER_ITEMS') == 'order_items'

    def test_get_explore_name_with_prefix_suffix(self, sample_config):
        """Test explore name generation with prefix and suffix."""
        sample_config['model_rules']['naming_conventions']['explore_prefix'] = 'exp_'
        sample_config['model_rules']['naming_conventions']['explore_suffix'] = '_analysis'

        generator = LookMLExploreGenerator(sample_config)

        assert generator._get_explore_name('users') == 'exp_users_analysis'

    def test_get_suggested_fields_comprehensive(self, sample_config, sample_table_metadata):
        """Test suggested fields generation."""
        generator = LookMLExploreGenerator(sample_config)
        suggested = generator._get_suggested_fields(sample_table_metadata)

        assert isinstance(suggested, list)
        assert len(suggested) <= 6  # Should limit to 6 fields

        # Should include primary key
        assert 'user_pk' in suggested

        # Should include string fields (email)
        assert 'email' in suggested

    def test_get_suggested_fields_no_primary_key(self, sample_config):
        """Test suggested fields when no primary key exists."""
        generator = LookMLExploreGenerator(sample_config)

        table_metadata = {
            'columns': [
                {'name': 'email', 'type': 'STRING'},
                {'name': 'name', 'type': 'STRING'},
                {'name': 'created_at', 'type': 'TIMESTAMP'}
            ]
        }

        suggested = generator._get_suggested_fields(table_metadata)

        # Should still include string and time fields
        assert 'email' in suggested
        assert 'name' in suggested
        assert 'created_at' in suggested

    def test_field_identification_methods(self, sample_config):
        """Test field identification helper methods."""
        generator = LookMLExploreGenerator(sample_config)

        # Test foreign key identification
        assert generator._is_foreign_key('organization_fk') is True
        assert generator._is_foreign_key('user_pk') is False

        # Test primary key identification
        assert generator._is_primary_key('user_pk') is True
        assert generator._is_primary_key('organization_fk') is False

        # Test field hiding
        assert generator._should_hide_field('user_pk') is True
        assert generator._should_hide_field('email') is False
