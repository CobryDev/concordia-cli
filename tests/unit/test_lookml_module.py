"""
Unit tests for lookml_module.py.

Tests the LookMLViewGenerator and LookMLDimensionGenerator classes
for view generation, dimension creation, and type mapping logic.
"""

from unittest.mock import patch

import pytest

from actions.looker.lookml_module import LookMLDimensionGenerator, LookMLViewGenerator
from actions.models.config import LookMLParams, TypeMapping
from actions.models.metadata import ColumnMetadata


class TestLookMLViewGenerator:
    """Test cases for LookMLViewGenerator class."""

    def test_init(self, sample_config):
        """Test initialization of LookMLViewGenerator."""
        generator = LookMLViewGenerator(sample_config)

        assert generator.config == sample_config
        assert generator.model_rules == sample_config.model_rules
        assert generator.looker_config == sample_config.looker
        assert generator.connection_name == "test-bigquery-connection"
        assert generator.field_identifier is not None

    def test_generate_view_dict_basic_structure(self, sample_config, sample_table_metadata):
        """Test basic view dictionary structure generation."""
        generator = LookMLViewGenerator(sample_config)
        result = generator.generate_view_dict(sample_table_metadata)

        # Check basic structure
        assert "view" in result
        assert "users" in result["view"]

        view = result["view"]["users"]
        assert view["sql_table_name"] == "`test-project.test_dataset.users`"
        # connection and view-level description are intentionally omitted in base views
        assert "connection" not in view
        assert "description" not in view

    def test_generate_view_dict_dimensions(self, sample_config, sample_table_metadata):
        """Test dimension generation in view dictionary."""
        generator = LookMLViewGenerator(sample_config)
        result = generator.generate_view_dict(sample_table_metadata)

        view = result["view"]["users"]

        # Should have dimensions for non-time fields
        assert "dimension" in view
        dimensions = view["dimension"]

        # Check specific dimensions exist
        dimension_names = []
        for dim in dimensions:
            dimension_names.extend(dim.keys())

        assert "email" in dimension_names
        assert "is_active" in dimension_names
        assert "organization_fk" in dimension_names

    def test_generate_view_dict_dimension_groups(self, sample_config, sample_table_metadata):
        """Test dimension group generation for time fields."""
        generator = LookMLViewGenerator(sample_config)
        result = generator.generate_view_dict(sample_table_metadata)

        view = result["view"]["users"]

        # Should have dimension groups for time fields
        assert "dimension_group" in view
        dimension_groups = view["dimension_group"]

        # Check that created_at timestamp becomes a dimension group
        group_names = []
        for group in dimension_groups:
            group_names.extend(group.keys())

        assert "created" in group_names  # '_at' suffix removed

    def test_generate_view_dict_drill_fields(self, sample_config, sample_table_metadata):
        """Test drill fields generation."""
        generator = LookMLViewGenerator(sample_config)
        result = generator.generate_view_dict(sample_table_metadata)

        view = result["view"]["users"]

        # Should have drill fields set in explicit-name form
        assert "set" in view
        assert "name" in view["set"]
        assert view["set"]["name"] == "all_fields"
        assert "fields" in view["set"]

        drill_fields = view["set"]["fields"]

        # Should include non-hidden fields
        assert "email" in drill_fields
        assert "is_active" in drill_fields
        # Hidden fields should not be in drill fields
        assert "user_pk" not in drill_fields
        assert "organization_fk" not in drill_fields

    def test_get_view_name_default(self, sample_config):
        """Test view name generation with default settings."""
        generator = LookMLViewGenerator(sample_config)

        assert generator._get_view_name("users") == "users"
        assert generator._get_view_name("ORDERS") == "orders"
        assert generator._get_view_name("Customer_Data") == "customer_data"

    def test_get_view_name_with_prefix_suffix(self, sample_config):
        """Test view name generation with prefix and suffix."""
        # Add naming conventions to config
        sample_config.model_rules.naming_conventions.view_prefix = "vw_"
        sample_config.model_rules.naming_conventions.view_suffix = "_view"

        generator = LookMLViewGenerator(sample_config)

        assert generator._get_view_name("users") == "vw_users_view"
        assert generator._get_view_name("orders") == "vw_orders_view"

    def test_generate_dimension_string_type(self, sample_config, sample_column_string):
        """Test dimension generation for string column."""
        generator = LookMLViewGenerator(sample_config)
        result = generator._generate_dimension(sample_column_string)

        assert result is not None
        assert "email" in result

        dimension = result["email"]
        assert dimension["type"] == "string"  # from lookml_params.type
        assert dimension["sql"] == "${TABLE}.email"
        assert dimension["description"] == "User email address"

    def test_generate_dimension_primary_key(self, sample_config, sample_column_primary_key):
        """Test dimension generation for primary key column."""
        generator = LookMLViewGenerator(sample_config)
        result = generator._generate_dimension(sample_column_primary_key)

        assert result is not None
        assert "user_pk" in result

        dimension = result["user_pk"]
        assert dimension["primary_key"] == "yes"
        assert dimension["hidden"] == "yes"  # Should be hidden based on config

    def test_generate_dimension_unsupported_type(self, sample_config):
        """Test dimension generation for unsupported BigQuery type."""
        from actions.models.metadata import ColumnMetadata

        unsupported_column = ColumnMetadata(
            name="geometry_field",
            type="GEOGRAPHY",  # Not in type mapping
            standardized_type="GEOGRAPHY",
        )

        generator = LookMLViewGenerator(sample_config)

        with patch("click.echo") as mock_echo:
            result = generator._generate_dimension(unsupported_column)

            assert result is None
            mock_echo.assert_called_once()
            assert "No type mapping found" in mock_echo.call_args[0][0]

    def test_generate_dimension_group_timestamp(self, sample_config, sample_column_timestamp):
        """Test dimension group generation for timestamp column."""
        generator = LookMLViewGenerator(sample_config)
        result = generator._generate_dimension_group(sample_column_timestamp)

        assert result is not None
        assert "created" in result  # '_at' suffix removed

        dim_group = result["created"]
        assert dim_group["type"] == "time"
        assert dim_group["sql"] == "${TABLE}.created_at"
        assert dim_group["description"] == "Account creation timestamp"
        assert "raw" in dim_group["timeframes"]
        assert "time" in dim_group["timeframes"]
        assert "date" in dim_group["timeframes"]

    def test_generate_dimension_group_date_type(self, sample_config):
        """Test dimension group generation for DATE column."""
        from actions.models.metadata import ColumnMetadata

        date_column = ColumnMetadata(
            name="birth_date",
            type="DATE",
            standardized_type="DATE",
            description="User birth date",
        )

        generator = LookMLViewGenerator(sample_config)
        result = generator._generate_dimension_group(date_column)

        assert result is not None
        assert "birth" in result  # '_date' suffix removed

        dim_group = result["birth"]
        assert dim_group["type"] == "time"
        assert "raw" in dim_group["timeframes"]
        assert "date" in dim_group["timeframes"]
        # Should not have 'time' timeframe for DATE type
        assert "time" not in dim_group["timeframes"]

    def test_generate_dimension_group_non_time_type(self, sample_config, sample_column_string):
        """Test dimension group generation returns None for non-time types."""
        generator = LookMLViewGenerator(sample_config)
        result = generator._generate_dimension_group(sample_column_string)

        assert result is None

    def test_is_time_dimension(self, sample_config):
        """Test time dimension identification."""
        generator = LookMLViewGenerator(sample_config)

        from actions.models.metadata import ColumnMetadata

        # Time types
        assert (
            generator._is_time_dimension(ColumnMetadata(name="test", type="TIMESTAMP", standardized_type="TIMESTAMP"))
            is True
        )
        assert (
            generator._is_time_dimension(ColumnMetadata(name="test", type="DATETIME", standardized_type="DATETIME"))
            is True
        )
        assert generator._is_time_dimension(ColumnMetadata(name="test", type="DATE", standardized_type="DATE")) is True
        assert generator._is_time_dimension(ColumnMetadata(name="test", type="TIME", standardized_type="TIME")) is True

        # Non-time types
        assert (
            generator._is_time_dimension(ColumnMetadata(name="test", type="STRING", standardized_type="STRING"))
            is False
        )
        assert (
            generator._is_time_dimension(ColumnMetadata(name="test", type="INTEGER", standardized_type="INTEGER"))
            is False
        )
        assert generator._is_time_dimension(ColumnMetadata(name="test", type="BOOL", standardized_type="BOOL")) is False

    def test_find_type_mapping(self, sample_config):
        """Test type mapping lookup."""
        generator = LookMLViewGenerator(sample_config)

        # Test existing mappings
        string_mapping = generator._find_type_mapping("STRING")
        assert string_mapping is not None
        assert string_mapping.lookml_type == "dimension"

        integer_mapping = generator._find_type_mapping("INTEGER")
        assert integer_mapping is not None
        assert integer_mapping.lookml_type == "dimension"

        # Test non-existing mapping
        unknown_mapping = generator._find_type_mapping("UNKNOWN_TYPE")
        assert unknown_mapping is None

    def test_should_hide_field(self, sample_config):
        """Test field hiding logic."""
        generator = LookMLViewGenerator(sample_config)

        # Fields that should be hidden
        assert generator._should_hide_field("user_pk") is True
        assert generator._should_hide_field("organization_fk") is True

        # Fields that should not be hidden
        assert generator._should_hide_field("email") is False
        assert generator._should_hide_field("created_at") is False

    def test_is_primary_key(self, sample_config):
        """Test primary key identification."""
        generator = LookMLViewGenerator(sample_config)

        # Primary key fields
        assert generator._is_primary_key("user_pk") is True
        assert generator._is_primary_key("id") is True

        # Non-primary key fields
        assert generator._is_primary_key("email") is False
        assert generator._is_primary_key("user_fk") is False

    def test_is_foreign_key(self, sample_config):
        """Test foreign key identification."""
        generator = LookMLViewGenerator(sample_config)

        # Foreign key fields
        assert generator._is_foreign_key("organization_fk") is True
        assert generator._is_foreign_key("user_fk") is True

        # Non-foreign key fields
        assert generator._is_foreign_key("email") is False
        assert generator._is_foreign_key("user_pk") is False

    @pytest.mark.parametrize(
        "bq_type,expected_lookml_type,expected_dimension_type",
        [
            ("STRING", "dimension", "string"),
            ("INTEGER", "dimension", "number"),
            ("INT64", "dimension", "number"),
            ("FLOAT64", "dimension", "number"),
            ("NUMERIC", "dimension", "number"),
            ("BOOL", "dimension", "yesno"),
            ("GEOGRAPHY", "dimension", "string"),
            ("TIMESTAMP", "dimension_group", "time"),
            ("DATE", "dimension_group", "time"),
        ],
    )
    def test_comprehensive_type_mapping(self, sample_config, bq_type, expected_lookml_type, expected_dimension_type):
        """Test all supported BigQuery type mappings comprehensively."""
        # Add comprehensive type mappings to the config
        comprehensive_mappings = [
            TypeMapping(
                bq_type="STRING",
                lookml_type="dimension",
                lookml_params=LookMLParams(type="string"),
            ),
            TypeMapping(
                bq_type="INTEGER",
                lookml_type="dimension",
                lookml_params=LookMLParams(type="number"),
            ),
            TypeMapping(
                bq_type="INT64",
                lookml_type="dimension",
                lookml_params=LookMLParams(type="number"),
            ),
            TypeMapping(
                bq_type="FLOAT64",
                lookml_type="dimension",
                lookml_params=LookMLParams(type="number"),
            ),
            TypeMapping(
                bq_type="NUMERIC",
                lookml_type="dimension",
                lookml_params=LookMLParams(type="number"),
            ),
            TypeMapping(
                bq_type="BOOL",
                lookml_type="dimension",
                lookml_params=LookMLParams(type="yesno"),
            ),
            TypeMapping(
                bq_type="GEOGRAPHY",
                lookml_type="dimension",
                lookml_params=LookMLParams(type="string"),
            ),
            TypeMapping(
                bq_type="TIMESTAMP",
                lookml_type="dimension_group",
                lookml_params=LookMLParams(
                    type="time",
                    timeframes="[raw, time, date, week, month, quarter, year]",
                ),
            ),
            TypeMapping(
                bq_type="DATE",
                lookml_type="dimension_group",
                lookml_params=LookMLParams(
                    type="time",
                    timeframes="[date, week, month, quarter, year]",
                ),
            ),
        ]

        # Replace the type mappings in the config
        sample_config.model_rules.type_mapping = comprehensive_mappings

        generator = LookMLViewGenerator(sample_config)

        # Find the type mapping
        type_mapping = generator._find_type_mapping(bq_type)
        assert type_mapping is not None, f"No mapping found for {bq_type}"
        assert type_mapping.lookml_type == expected_lookml_type
        assert type_mapping.lookml_params.type == expected_dimension_type

        # Test dimension generation for non-time types
        if expected_lookml_type == "dimension":
            column = ColumnMetadata(
                name=f"test_{bq_type.lower()}_field",
                type=bq_type,
                standardized_type=bq_type,
                description=f"Test {bq_type} field",
            )

            result = generator._generate_dimension(column)
            assert result is not None

            field_name = f"test_{bq_type.lower()}_field"
            assert field_name in result
            dimension = result[field_name]
            assert dimension["type"] == expected_dimension_type
            assert dimension["sql"] == f"${{TABLE}}.{field_name}"
            assert dimension["description"] == f"Test {bq_type} field"

        # Test dimension group generation for time types
        elif expected_lookml_type == "dimension_group":
            column = ColumnMetadata(
                name=f"test_{bq_type.lower()}_timestamp",
                type=bq_type,
                standardized_type=bq_type,
                description=f"Test {bq_type} timestamp",
            )

            result = generator._generate_dimension_group(column)
            assert result is not None

            # Dimension groups have suffix removed
            # '_timestamp' suffix removed
            field_name = f"test_{bq_type.lower()}"
            assert field_name in result
            dim_group = result[field_name]
            assert dim_group["type"] == expected_dimension_type
            assert dim_group["sql"] == f"${{TABLE}}.test_{bq_type.lower()}_timestamp"

    @pytest.mark.parametrize(
        "bq_type,expected_timeframes",
        [
            ("TIMESTAMP", ["raw", "time", "date", "week", "month", "quarter", "year"]),
            ("DATETIME", ["raw", "time", "date", "week", "month", "quarter", "year"]),
            ("DATE", ["raw", "date", "week", "month", "quarter", "year"]),
        ],
    )
    def test_dimension_group_timeframes_by_type(self, sample_config, bq_type, expected_timeframes):
        """Test that different time types generate appropriate timeframes."""
        generator = LookMLViewGenerator(sample_config)

        column = ColumnMetadata(
            name=f"test_{bq_type.lower()}_field",
            type=bq_type,
            standardized_type=bq_type,
            description=f"Test {bq_type} field",
        )

        result = generator._generate_dimension_group(column)
        assert result is not None

        # Get the dimension group name - suffix "_field" is not removed by the implementation
        # Only time-related suffixes like _at, _date, _time, _ts, _timestamp are removed
        dim_group_name = f"test_{bq_type.lower()}_field"
        assert dim_group_name in result

        dim_group = result[dim_group_name]
        assert dim_group["type"] == "time"
        assert dim_group["timeframes"] == expected_timeframes

    @pytest.mark.parametrize(
        "column_name,expected_group_name",
        [
            ("created_at", "created"),
            ("updated_at", "updated"),
            ("deleted_at", "deleted"),
            ("birth_date", "birth"),
            ("expiry_date", "expiry"),
            ("start_time", "start"),
            ("end_time", "end"),
            ("processed_ts", "processed"),
            ("generated_timestamp", "generated"),
            ("event_datetime", "event_datetime"),  # No suffix to remove
            ("timestamp", "timestamp"),  # No suffix to remove
            # _utc is not a recognized time suffix
            ("created_at_utc", "created_at_utc"),
        ],
    )
    def test_dimension_group_suffix_removal(self, sample_config, column_name, expected_group_name):
        """Test that dimension groups properly remove common time suffixes."""
        generator = LookMLViewGenerator(sample_config)

        column = ColumnMetadata(
            name=column_name,
            type="TIMESTAMP",
            standardized_type="TIMESTAMP",
            description=f"Test timestamp field: {column_name}",
        )

        result = generator._generate_dimension_group(column)
        assert result is not None
        assert expected_group_name in result

        dim_group = result[expected_group_name]
        assert dim_group["sql"] == f"${{TABLE}}.{column_name}"
        assert dim_group["type"] == "time"

    def test_dimension_group_datetime_type(self, sample_config):
        """Test dimension group generation specifically for DATETIME type."""
        generator = LookMLViewGenerator(sample_config)

        datetime_column = ColumnMetadata(
            name="event_datetime",
            type="DATETIME",
            standardized_type="DATETIME",
            description="Event datetime",
        )

        result = generator._generate_dimension_group(datetime_column)
        assert result is not None
        assert "event_datetime" in result

        dim_group = result["event_datetime"]
        assert dim_group["type"] == "time"
        assert dim_group["sql"] == "${TABLE}.event_datetime"
        assert dim_group["description"] == "Event datetime"

        # DATETIME should have time and date timeframes
        expected_timeframes = ["raw", "time", "date", "week", "month", "quarter", "year"]
        assert dim_group["timeframes"] == expected_timeframes

    def test_time_dimension_identification_comprehensive(self, sample_config):
        """Test comprehensive time dimension identification for all time types."""
        generator = LookMLViewGenerator(sample_config)

        # Test all time types
        time_types = ["TIMESTAMP", "DATETIME", "DATE", "TIME"]
        for time_type in time_types:
            column = ColumnMetadata(
                name=f"test_{time_type.lower()}_field",
                type=time_type,
                standardized_type=time_type,
            )
            assert generator._is_time_dimension(column) is True, f"{time_type} should be identified as time dimension"

        # Test non-time types
        non_time_types = ["STRING", "INTEGER", "FLOAT64", "BOOL", "GEOGRAPHY"]
        for non_time_type in non_time_types:
            column = ColumnMetadata(
                name=f"test_{non_time_type.lower()}_field",
                type=non_time_type,
                standardized_type=non_time_type,
            )
            assert generator._is_time_dimension(column) is False, (
                f"{non_time_type} should not be identified as time dimension"
            )

    def test_edge_case_types(self, sample_config):
        """Test handling of edge case and less common BigQuery types."""
        generator = LookMLViewGenerator(sample_config)

        # Test unsupported types that might be encountered
        unsupported_types = ["ARRAY", "STRUCT", "JSON", "BYTES"]

        for unsupported_type in unsupported_types:
            column = ColumnMetadata(
                name=f"test_{unsupported_type.lower()}_field",
                type=unsupported_type,
                standardized_type=unsupported_type,
            )

            with patch("click.echo") as mock_echo:
                result = generator._generate_dimension(column)
                assert result is None
                mock_echo.assert_called_once()
                assert "No type mapping found" in mock_echo.call_args[0][0]

    def test_hidden_field_dimension_group(self, sample_config):
        """Test that dimension groups respect hidden field configuration."""
        generator = LookMLViewGenerator(sample_config)

        # Test with a timestamp field that should be hidden (ends with _fk suffix)
        hidden_timestamp = ColumnMetadata(
            name="created_at_fk",  # This would be weird in practice but tests the logic
            type="TIMESTAMP",
            standardized_type="TIMESTAMP",
            description="Hidden timestamp field",
        )

        result = generator._generate_dimension_group(hidden_timestamp)
        assert result is not None

        # Should still generate but mark as hidden
        # Note: Only time-related suffixes are removed, so _fk stays in the dimension group name
        assert "created_at_fk" in result
        dim_group = result["created_at_fk"]
        assert dim_group["hidden"] == "yes"


class TestLookMLDimensionGenerator:
    """Test cases for LookMLDimensionGenerator class."""

    def test_init(self, sample_config):
        """Test initialization of LookMLDimensionGenerator."""
        generator = LookMLDimensionGenerator(sample_config)

        assert generator.config == sample_config
        assert generator.model_rules == sample_config.model_rules

    def test_generate_case_dimension_basic(self, sample_config):
        """Test basic case dimension generation."""
        from actions.models.metadata import ColumnMetadata

        column = ColumnMetadata(name="status", type="STRING", standardized_type="STRING")

        case_logic = {
            "name": "status_category",
            "description": "Status category",
            "conditions": [
                {"condition": '${TABLE}.status = "active"', "value": "Active"},
                {"condition": '${TABLE}.status = "inactive"', "value": "Inactive"},
            ],
            "default": "Unknown",
        }

        generator = LookMLDimensionGenerator(sample_config)
        result = generator.generate_case_dimension(column, case_logic)

        assert "status_category" in result
        dimension = result["status_category"]
        assert dimension["type"] == "string"
        assert dimension["description"] == "Status category"
        assert "CASE" in dimension["sql"]
        assert "WHEN" in dimension["sql"]
        assert "Active" in dimension["sql"]
        assert "Unknown" in dimension["sql"]

    def test_generate_case_dimension_default_name(self, sample_config):
        """Test case dimension generation with default name."""
        from actions.models.metadata import ColumnMetadata

        column = ColumnMetadata(name="priority", type="INTEGER", standardized_type="INTEGER")

        case_logic = {"conditions": [{"condition": "${TABLE}.priority > 5", "value": "High"}]}

        generator = LookMLDimensionGenerator(sample_config)
        result = generator.generate_case_dimension(column, case_logic)

        assert "priority_category" in result
        dimension = result["priority_category"]
        assert dimension["description"] == "Categorized priority"
        assert "Other" in dimension["sql"]  # Default value

    def test_generate_yesno_dimension_boolean(self, sample_config):
        """Test yes/no dimension generation for boolean column."""
        from actions.models.metadata import ColumnMetadata

        boolean_column = ColumnMetadata(
            name="is_verified",
            type="BOOLEAN",
            standardized_type="BOOLEAN",
            description="Whether user is verified",
        )

        generator = LookMLDimensionGenerator(sample_config)
        result = generator.generate_yesno_dimension(boolean_column)

        assert "is_verified" in result
        dimension = result["is_verified"]
        assert dimension["type"] == "yesno"
        assert dimension["sql"] == "${TABLE}.is_verified"
        assert dimension["description"] == "Whether user is verified"

    def test_generate_yesno_dimension_numeric(self, sample_config):
        """Test yes/no dimension generation for numeric column."""
        from actions.models.metadata import ColumnMetadata

        numeric_column = ColumnMetadata(name="login_count", type="INTEGER", standardized_type="INTEGER")

        generator = LookMLDimensionGenerator(sample_config)
        result = generator.generate_yesno_dimension(numeric_column)

        assert "login_count" in result
        dimension = result["login_count"]
        assert dimension["type"] == "yesno"
        assert dimension["sql"] == "${TABLE}.login_count > 0"
        assert "Yes/No indicator for login_count" in dimension["description"]

    def test_generate_yesno_dimension_no_description(self, sample_config):
        """Test yes/no dimension generation without description."""
        from actions.models.metadata import ColumnMetadata

        column = ColumnMetadata(name="has_orders", type="INTEGER", standardized_type="INTEGER")

        generator = LookMLDimensionGenerator(sample_config)
        result = generator.generate_yesno_dimension(column)

        assert "has_orders" in result
        dimension = result["has_orders"]
        assert dimension["description"] == "Yes/No indicator for has_orders"
