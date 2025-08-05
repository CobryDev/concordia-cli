"""
Unit tests for field_utils.py module.

Tests the FieldIdentifier class which handles field type identification
based on naming conventions.
"""

import pytest
from actions.looker.field_utils import FieldIdentifier
from actions.models.config import ModelRules, NamingConventions, DefaultBehaviors, TypeMapping, LookMLParams


class TestFieldIdentifier:
    """Test cases for FieldIdentifier class."""

    def test_init_with_default_values(self):
        """Test initialization with default naming conventions."""
        model_rules = ModelRules(
            naming_conventions=NamingConventions(),
            defaults=DefaultBehaviors(),
            type_mapping=[]
        )
        identifier = FieldIdentifier(model_rules)

        assert identifier.model_rules == model_rules

    def test_init_with_custom_naming_conventions(self):
        """Test initialization with custom naming conventions."""
        model_rules = ModelRules(
            naming_conventions=NamingConventions(
                pk_suffix='_id',
                fk_suffix='_ref'
            ),
            defaults=DefaultBehaviors(),
            type_mapping=[]
        )
        identifier = FieldIdentifier(model_rules)

        assert identifier.model_rules == model_rules

    def test_is_primary_key_with_default_suffix(self):
        """Test primary key identification with default '_pk' suffix."""
        model_rules = ModelRules(
            naming_conventions=NamingConventions(),
            defaults=DefaultBehaviors(),
            type_mapping=[]
        )
        identifier = FieldIdentifier(model_rules)

        # Test default _pk suffix
        assert identifier.is_primary_key('user_pk') is True
        assert identifier.is_primary_key('order_pk') is True

        # Test 'id' field
        assert identifier.is_primary_key('id') is True

        # Test non-primary key fields
        assert identifier.is_primary_key('email') is False
        assert identifier.is_primary_key('user_fk') is False
        assert identifier.is_primary_key('created_at') is False

    def test_is_primary_key_with_custom_suffix(self):
        """Test primary key identification with custom suffix."""
        model_rules = ModelRules(
            naming_conventions=NamingConventions(pk_suffix='_id'),
            defaults=DefaultBehaviors(),
            type_mapping=[]
        )
        identifier = FieldIdentifier(model_rules)

        # Test custom _id suffix
        assert identifier.is_primary_key('user_id') is True
        assert identifier.is_primary_key('order_id') is True

        # Test 'id' field still works
        assert identifier.is_primary_key('id') is True

        # Test default _pk suffix doesn't work with custom config
        assert identifier.is_primary_key('user_pk') is False

    def test_is_foreign_key_with_default_suffix(self):
        """Test foreign key identification with default '_fk' suffix."""
        model_rules = ModelRules(
            naming_conventions=NamingConventions(),
            defaults=DefaultBehaviors(),
            type_mapping=[]
        )
        identifier = FieldIdentifier(model_rules)

        # Test default _fk suffix
        assert identifier.is_foreign_key('organization_fk') is True
        assert identifier.is_foreign_key('user_fk') is True

        # Test non-foreign key fields
        assert identifier.is_foreign_key('email') is False
        assert identifier.is_foreign_key('user_pk') is False
        assert identifier.is_foreign_key('created_at') is False

    def test_is_foreign_key_with_custom_suffix(self):
        """Test foreign key identification with custom suffix."""
        model_rules = ModelRules(
            naming_conventions=NamingConventions(fk_suffix='_ref'),
            defaults=DefaultBehaviors(),
            type_mapping=[]
        )
        identifier = FieldIdentifier(model_rules)

        # Test custom _ref suffix
        assert identifier.is_foreign_key('organization_ref') is True
        assert identifier.is_foreign_key('user_ref') is True

        # Test default _fk suffix doesn't work with custom config
        assert identifier.is_foreign_key('organization_fk') is False

    def test_should_hide_field_with_default_config(self):
        """Test field hiding with default configuration."""
        model_rules = ModelRules(
            naming_conventions=NamingConventions(),
            defaults=DefaultBehaviors(hide_fields_by_suffix=['_pk', '_fk']),
            type_mapping=[]
        )
        identifier = FieldIdentifier(model_rules)

        # Test hidden fields
        assert identifier.should_hide_field('user_pk') is True
        assert identifier.should_hide_field('organization_fk') is True

        # Test visible fields
        assert identifier.should_hide_field('email') is False
        assert identifier.should_hide_field('created_at') is False

    def test_should_hide_field_with_custom_config(self):
        """Test field hiding with custom configuration."""
        model_rules = ModelRules(
            naming_conventions=NamingConventions(),
            defaults=DefaultBehaviors(
                hide_fields_by_suffix=['_id', '_internal']),
            type_mapping=[]
        )
        identifier = FieldIdentifier(model_rules)

        # Test hidden fields
        assert identifier.should_hide_field('user_id') is True
        assert identifier.should_hide_field('debug_internal') is True

        # Test visible fields
        assert identifier.should_hide_field('user_pk') is False
        assert identifier.should_hide_field('email') is False

    def test_should_hide_field_with_empty_config(self):
        """Test field hiding with empty configuration."""
        model_rules = ModelRules(
            naming_conventions=NamingConventions(),
            defaults=DefaultBehaviors(hide_fields_by_suffix=[]),
            type_mapping=[]
        )
        identifier = FieldIdentifier(model_rules)

        # No fields should be hidden without configuration
        assert identifier.should_hide_field('user_pk') is False
        assert identifier.should_hide_field('organization_fk') is False
        assert identifier.should_hide_field('email') is False

    def test_get_foreign_key_suffix_default(self):
        """Test getting foreign key suffix with default configuration."""
        model_rules = ModelRules(
            naming_conventions=NamingConventions(),
            defaults=DefaultBehaviors(),
            type_mapping=[]
        )
        identifier = FieldIdentifier(model_rules)

        assert identifier.get_foreign_key_suffix() == '_fk'

    def test_get_foreign_key_suffix_custom(self):
        """Test getting foreign key suffix with custom configuration."""
        model_rules = ModelRules(
            naming_conventions=NamingConventions(fk_suffix='_ref'),
            defaults=DefaultBehaviors(),
            type_mapping=[]
        )
        identifier = FieldIdentifier(model_rules)

        assert identifier.get_foreign_key_suffix() == '_ref'

    def test_get_primary_key_suffix_default(self):
        """Test getting primary key suffix with default configuration."""
        model_rules = ModelRules(
            naming_conventions=NamingConventions(),
            defaults=DefaultBehaviors(),
            type_mapping=[]
        )
        identifier = FieldIdentifier(model_rules)

        assert identifier.get_primary_key_suffix() == '_pk'

    def test_get_primary_key_suffix_custom(self):
        """Test getting primary key suffix with custom configuration."""
        model_rules = ModelRules(
            naming_conventions=NamingConventions(pk_suffix='_id'),
            defaults=DefaultBehaviors(),
            type_mapping=[]
        )
        identifier = FieldIdentifier(model_rules)

        assert identifier.get_primary_key_suffix() == '_id'

    def test_infer_table_name_from_foreign_key_default_suffix(self):
        """Test table name inference from foreign key with default suffix."""
        model_rules = ModelRules(
            naming_conventions=NamingConventions(),
            defaults=DefaultBehaviors(),
            type_mapping=[]
        )
        identifier = FieldIdentifier(model_rules)

        # Test with _fk suffix
        assert identifier.infer_table_name_from_foreign_key(
            'organization_fk') == 'organizations'
        assert identifier.infer_table_name_from_foreign_key(
            'user_fk') == 'users'

        # Test with _id suffix (backward compatibility)
        assert identifier.infer_table_name_from_foreign_key(
            'organization_id') == 'organizations'
        assert identifier.infer_table_name_from_foreign_key(
            'user_id') == 'users'

        # Test with non-foreign key field
        assert identifier.infer_table_name_from_foreign_key('email') is None

    def test_infer_table_name_from_foreign_key_custom_suffix(self):
        """Test table name inference from foreign key with custom suffix."""
        model_rules = ModelRules(
            naming_conventions=NamingConventions(fk_suffix='_ref'),
            defaults=DefaultBehaviors(),
            type_mapping=[]
        )
        identifier = FieldIdentifier(model_rules)

        # Test with custom _ref suffix
        assert identifier.infer_table_name_from_foreign_key(
            'organization_ref') == 'organizations'
        assert identifier.infer_table_name_from_foreign_key(
            'user_ref') == 'users'

        # Test with _id suffix (backward compatibility still works)
        assert identifier.infer_table_name_from_foreign_key(
            'organization_id') == 'organizations'

        # Test that default _fk suffix doesn't work with custom config
        assert identifier.infer_table_name_from_foreign_key(
            'organization_fk') is None

    def test_infer_table_name_edge_cases(self):
        """Test edge cases for table name inference."""
        model_rules = ModelRules(
            naming_conventions=NamingConventions(),
            defaults=DefaultBehaviors(),
            type_mapping=[]
        )
        identifier = FieldIdentifier(model_rules)

        # Test empty string
        assert identifier.infer_table_name_from_foreign_key('') is None

        # Test field that ends with suffix but results in empty base name
        # Note: Current implementation returns 's' for '_fk' (empty base + 's')
        assert identifier.infer_table_name_from_foreign_key('_fk') == 's'
        assert identifier.infer_table_name_from_foreign_key('_id') == 's'

        # Test complex names
        assert identifier.infer_table_name_from_foreign_key(
            'parent_organization_fk') == 'parent_organizations'

    def test_multiple_suffixes_in_hide_fields(self):
        """Test hiding fields with multiple suffix patterns."""
        model_rules = ModelRules(
            naming_conventions=NamingConventions(),
            defaults=DefaultBehaviors(hide_fields_by_suffix=[
                                      '_pk', '_fk', '_internal', '_temp']),
            type_mapping=[]
        )
        identifier = FieldIdentifier(model_rules)

        # Test all configured suffixes
        assert identifier.should_hide_field('user_pk') is True
        assert identifier.should_hide_field('org_fk') is True
        assert identifier.should_hide_field('debug_internal') is True
        assert identifier.should_hide_field('cache_temp') is True

        # Test non-matching field
        assert identifier.should_hide_field('email') is False
