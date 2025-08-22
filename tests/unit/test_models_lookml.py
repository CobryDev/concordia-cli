"""
Unit tests for Pydantic models in actions/models/lookml.py.

Tests serialization logic, to_dict() methods, and LookML-specific formatting
for dimension, measure, and view models used in LookML generation.
"""

import pytest
from pydantic import ValidationError

from actions.models.lookml import (
    Dimension,
    DimensionGroup,
    DimensionGroupType,
    DimensionType,
    LookMLProject,
    LookMLView,
    Measure,
    MeasureType,
)


class TestDimension:
    """Test Dimension model and serialization logic."""

    def test_valid_dimension_creation(self):
        """Test creation of valid dimension."""
        dimension = Dimension(
            name="user_id",
            type=DimensionType.NUMBER,
            sql="${TABLE}.user_id",
            description="Unique user identifier",
            label="User ID",
            hidden=True,
            primary_key=True,
        )

        assert dimension.name == "user_id"
        assert dimension.type == DimensionType.NUMBER
        assert dimension.sql == "${TABLE}.user_id"
        assert dimension.description == "Unique user identifier"
        assert dimension.label == "User ID"
        assert dimension.hidden is True
        assert dimension.primary_key is True

    def test_dimension_defaults(self):
        """Test default values for optional fields."""
        dimension = Dimension(name="test_field", type=DimensionType.STRING)

        assert dimension.sql is None
        assert dimension.description is None
        assert dimension.label is None
        assert dimension.hidden is False
        assert dimension.primary_key is False
        assert dimension.group_label is None
        assert dimension.value_format is None
        assert dimension.drill_fields is None
        assert dimension.additional_params == {}

    def test_dimension_name_validator_empty(self):
        """Test dimension name validator rejects empty names."""
        with pytest.raises(ValidationError) as exc_info:
            Dimension(name="", type=DimensionType.STRING)
        assert "Dimension name cannot be empty" in str(exc_info.value)

    def test_dimension_name_validator_whitespace_only(self):
        """Test dimension name validator rejects whitespace-only names."""
        with pytest.raises(ValidationError) as exc_info:
            Dimension(name="   ", type=DimensionType.STRING)
        assert "Dimension name cannot be empty" in str(exc_info.value)

    def test_dimension_name_validator_strips_whitespace(self):
        """Test dimension name validator strips whitespace."""
        dimension = Dimension(name="  test_field  ", type=DimensionType.STRING)
        assert dimension.name == "test_field"

    def test_dimension_to_dict_basic(self):
        """Test basic to_dict conversion with required fields only."""
        dimension = Dimension(name="user_name", type=DimensionType.STRING)

        result = dimension.to_dict()

        expected = {
            "name": "user_name",
            "type": "string",
        }
        assert result == expected

    def test_dimension_to_dict_with_optional_fields(self):
        """Test to_dict conversion with optional fields."""
        dimension = Dimension(
            name="user_id",
            type=DimensionType.NUMBER,
            sql="${TABLE}.user_id",
            description="User identifier",
            label="User ID",
            group_label="User Info",
            value_format="#,##0",
        )

        result = dimension.to_dict()

        expected = {
            "name": "user_id",
            "type": "number",
            "sql": "${TABLE}.user_id",
            "description": "User identifier",
            "label": "User ID",
            "group_label": "User Info",
            "value_format": "#,##0",
        }
        assert result == expected

    def test_dimension_to_dict_boolean_conversion_hidden(self):
        """Test to_dict converts hidden=True to 'yes' string."""
        dimension = Dimension(
            name="hidden_field",
            type=DimensionType.STRING,
            hidden=True,
        )

        result = dimension.to_dict()

        assert result["hidden"] == "yes"

        # Test that False doesn't add the field
        dimension_visible = Dimension(
            name="visible_field",
            type=DimensionType.STRING,
            hidden=False,
        )

        result_visible = dimension_visible.to_dict()
        assert "hidden" not in result_visible

    def test_dimension_to_dict_boolean_conversion_primary_key(self):
        """Test to_dict converts primary_key=True to 'yes' string."""
        dimension = Dimension(
            name="id_field",
            type=DimensionType.NUMBER,
            primary_key=True,
        )

        result = dimension.to_dict()

        assert result["primary_key"] == "yes"

        # Test that False doesn't add the field
        dimension_non_pk = Dimension(
            name="regular_field",
            type=DimensionType.STRING,
            primary_key=False,
        )

        result_non_pk = dimension_non_pk.to_dict()
        assert "primary_key" not in result_non_pk

    def test_dimension_to_dict_drill_fields_conversion(self):
        """Test to_dict converts drill_fields list to string."""
        dimension = Dimension(
            name="summary_field",
            type=DimensionType.STRING,
            drill_fields=["field1", "field2", "field3"],
        )

        result = dimension.to_dict()

        assert result["drill_fields"] == "['field1', 'field2', 'field3']"

    def test_dimension_to_dict_additional_params(self):
        """Test to_dict includes additional parameters."""
        dimension = Dimension(
            name="custom_field",
            type=DimensionType.STRING,
            additional_params={
                "custom_param": "custom_value",
                "another_param": 123,
            },
        )

        result = dimension.to_dict()

        assert result["custom_param"] == "custom_value"
        assert result["another_param"] == 123


class TestDimensionGroup:
    """Test DimensionGroup model and serialization logic."""

    def test_valid_dimension_group_creation(self):
        """Test creation of valid dimension group."""
        dim_group = DimensionGroup(
            name="created",
            type=DimensionGroupType.TIME,
            sql="${TABLE}.created_at",
            description="Creation timestamp",
            timeframes=["raw", "time", "date", "week"],
            convert_tz=False,
            datatype="timestamp",
        )

        assert dim_group.name == "created"
        assert dim_group.type == DimensionGroupType.TIME
        assert dim_group.sql == "${TABLE}.created_at"
        assert dim_group.description == "Creation timestamp"
        assert dim_group.timeframes == ["raw", "time", "date", "week"]
        assert dim_group.convert_tz is False
        assert dim_group.datatype == "timestamp"

    def test_dimension_group_defaults(self):
        """Test default values for optional fields."""
        dim_group = DimensionGroup(name="test_time", type=DimensionGroupType.TIME)

        assert dim_group.sql is None
        assert dim_group.description is None
        assert dim_group.label is None
        assert dim_group.timeframes is None
        assert dim_group.convert_tz is True
        assert dim_group.datatype is None
        assert dim_group.intervals is None
        assert dim_group.additional_params == {}

    def test_dimension_group_name_validator_empty(self):
        """Test dimension group name validator rejects empty names."""
        with pytest.raises(ValidationError) as exc_info:
            DimensionGroup(name="", type=DimensionGroupType.TIME)
        assert "Dimension group name cannot be empty" in str(exc_info.value)

    def test_dimension_group_name_validator_strips_whitespace(self):
        """Test dimension group name validator strips whitespace."""
        dim_group = DimensionGroup(name="  test_time  ", type=DimensionGroupType.TIME)
        assert dim_group.name == "test_time"

    def test_dimension_group_to_dict_basic(self):
        """Test basic to_dict conversion with required fields only."""
        dim_group = DimensionGroup(name="created", type=DimensionGroupType.TIME)

        result = dim_group.to_dict()

        expected = {
            "name": "created",
            "type": "time",
        }
        assert result == expected

    def test_dimension_group_to_dict_with_optional_fields(self):
        """Test to_dict conversion with optional fields."""
        dim_group = DimensionGroup(
            name="created",
            type=DimensionGroupType.TIME,
            sql="${TABLE}.created_at",
            description="Creation time",
            label="Created",
            timeframes=["time", "date", "week", "month"],
            datatype="timestamp",
        )

        result = dim_group.to_dict()

        expected = {
            "name": "created",
            "type": "time",
            "sql": "${TABLE}.created_at",
            "description": "Creation time",
            "label": "Created",
            "timeframes": ["time", "date", "week", "month"],
            "datatype": "timestamp",
        }
        assert result == expected

    def test_dimension_group_to_dict_convert_tz_false(self):
        """Test to_dict converts convert_tz=False to 'no' string."""
        dim_group = DimensionGroup(
            name="utc_time",
            type=DimensionGroupType.TIME,
            convert_tz=False,
        )

        result = dim_group.to_dict()

        assert result["convert_tz"] == "no"

        # Test that True doesn't add the field (default behavior)
        dim_group_convert = DimensionGroup(
            name="local_time",
            type=DimensionGroupType.TIME,
            convert_tz=True,
        )

        result_convert = dim_group_convert.to_dict()
        assert "convert_tz" not in result_convert

    def test_dimension_group_to_dict_duration_type(self):
        """Test to_dict with duration type and intervals."""
        dim_group = DimensionGroup(
            name="duration",
            type=DimensionGroupType.DURATION,
            sql="${TABLE}.duration_seconds",
            intervals=["second", "minute", "hour", "day"],
        )

        result = dim_group.to_dict()

        expected = {
            "name": "duration",
            "type": "duration",
            "sql": "${TABLE}.duration_seconds",
            "intervals": ["second", "minute", "hour", "day"],
        }
        assert result == expected


class TestMeasure:
    """Test Measure model and serialization logic."""

    def test_valid_measure_creation(self):
        """Test creation of valid measure."""
        measure = Measure(
            name="total_revenue",
            type=MeasureType.SUM,
            sql="${TABLE}.revenue",
            description="Total revenue amount",
            label="Total Revenue",
            hidden=True,
            value_format="$#,##0.00",
            filters={"status": "active"},
        )

        assert measure.name == "total_revenue"
        assert measure.type == MeasureType.SUM
        assert measure.sql == "${TABLE}.revenue"
        assert measure.description == "Total revenue amount"
        assert measure.label == "Total Revenue"
        assert measure.hidden is True
        assert measure.value_format == "$#,##0.00"
        assert measure.filters == {"status": "active"}

    def test_measure_defaults(self):
        """Test default values for optional fields."""
        measure = Measure(name="count", type=MeasureType.COUNT)

        assert measure.sql is None
        assert measure.description is None
        assert measure.label is None
        assert measure.hidden is False
        assert measure.group_label is None
        assert measure.value_format is None
        assert measure.drill_fields is None
        assert measure.filters is None
        assert measure.additional_params == {}

    def test_measure_name_validator_empty(self):
        """Test measure name validator rejects empty names."""
        with pytest.raises(ValidationError) as exc_info:
            Measure(name="", type=MeasureType.COUNT)
        assert "Measure name cannot be empty" in str(exc_info.value)

    def test_measure_name_validator_strips_whitespace(self):
        """Test measure name validator strips whitespace."""
        measure = Measure(name="  count_users  ", type=MeasureType.COUNT)
        assert measure.name == "count_users"

    def test_measure_to_dict_basic(self):
        """Test basic to_dict conversion with required fields only."""
        measure = Measure(name="count", type=MeasureType.COUNT)

        result = measure.to_dict()

        expected = {
            "name": "count",
            "type": "count",
        }
        assert result == expected

    def test_measure_to_dict_with_optional_fields(self):
        """Test to_dict conversion with optional fields."""
        measure = Measure(
            name="avg_price",
            type=MeasureType.AVERAGE,
            sql="${TABLE}.price",
            description="Average price",
            label="Avg Price",
            group_label="Pricing",
            value_format="$#,##0.00",
        )

        result = measure.to_dict()

        expected = {
            "name": "avg_price",
            "type": "average",
            "sql": "${TABLE}.price",
            "description": "Average price",
            "label": "Avg Price",
            "group_label": "Pricing",
            "value_format": "$#,##0.00",
        }
        assert result == expected

    def test_measure_to_dict_boolean_conversion_hidden(self):
        """Test to_dict converts hidden=True to 'yes' string."""
        measure = Measure(
            name="internal_metric",
            type=MeasureType.COUNT,
            hidden=True,
        )

        result = measure.to_dict()

        assert result["hidden"] == "yes"

    def test_measure_to_dict_drill_fields_conversion(self):
        """Test to_dict converts drill_fields list to string."""
        measure = Measure(
            name="total_sales",
            type=MeasureType.SUM,
            drill_fields=["date", "product", "region"],
        )

        result = measure.to_dict()

        assert result["drill_fields"] == "['date', 'product', 'region']"

    def test_measure_to_dict_filters_conversion(self):
        """Test to_dict converts filters dict to string."""
        measure = Measure(
            name="active_users",
            type=MeasureType.COUNT_DISTINCT,
            filters={"status": "active", "verified": "yes"},
        )

        result = measure.to_dict()

        assert result["filters"] == "{'status': 'active', 'verified': 'yes'}"


class TestLookMLView:
    """Test LookMLView model and serialization logic."""

    def create_sample_fields(self):
        """Helper to create sample fields for testing."""
        dimension = Dimension(name="id", type=DimensionType.NUMBER, primary_key=True)
        dim_group = DimensionGroup(name="created", type=DimensionGroupType.TIME)
        measure = Measure(name="count", type=MeasureType.COUNT)

        return dimension, dim_group, measure

    def test_valid_lookml_view_creation(self):
        """Test creation of valid LookML view."""
        dimension, dim_group, measure = self.create_sample_fields()

        view = LookMLView(
            name="users",
            sql_table_name="analytics.users",
            connection="bigquery_conn",
            description="User data view",
            dimensions=[dimension],
            dimension_groups=[dim_group],
            measures=[measure],
            drill_fields=["id", "name"],
        )

        assert view.name == "users"
        assert view.sql_table_name == "analytics.users"
        assert view.connection == "bigquery_conn"
        assert view.description == "User data view"
        assert len(view.dimensions) == 1
        assert len(view.dimension_groups) == 1
        assert len(view.measures) == 1
        assert view.drill_fields == ["id", "name"]

    def test_lookml_view_defaults(self):
        """Test default values for optional fields."""
        view = LookMLView(name="test_view", sql_table_name="test.table")

        assert view.connection is None
        assert view.description is None
        assert view.dimensions == []
        assert view.dimension_groups == []
        assert view.measures == []
        assert view.drill_fields is None
        assert view.additional_params == {}

    def test_lookml_view_name_validator_empty(self):
        """Test view name validator rejects empty names."""
        with pytest.raises(ValidationError) as exc_info:
            LookMLView(name="", sql_table_name="test.table")
        assert "View name cannot be empty" in str(exc_info.value)

    def test_lookml_view_name_validator_strips_whitespace(self):
        """Test view name validator strips whitespace."""
        view = LookMLView(name="  test_view  ", sql_table_name="test.table")
        assert view.name == "test_view"

    def test_lookml_view_add_dimension(self):
        """Test add_dimension method."""
        view = LookMLView(name="test_view", sql_table_name="test.table")
        dimension = Dimension(name="test_field", type=DimensionType.STRING)

        view.add_dimension(dimension)

        assert len(view.dimensions) == 1
        assert view.dimensions[0].name == "test_field"

    def test_lookml_view_add_dimension_group(self):
        """Test add_dimension_group method."""
        view = LookMLView(name="test_view", sql_table_name="test.table")
        dim_group = DimensionGroup(name="created", type=DimensionGroupType.TIME)

        view.add_dimension_group(dim_group)

        assert len(view.dimension_groups) == 1
        assert view.dimension_groups[0].name == "created"

    def test_lookml_view_add_measure(self):
        """Test add_measure method."""
        view = LookMLView(name="test_view", sql_table_name="test.table")
        measure = Measure(name="count", type=MeasureType.COUNT)

        view.add_measure(measure)

        assert len(view.measures) == 1
        assert view.measures[0].name == "count"

    def test_lookml_view_get_dimension_by_name_found(self):
        """Test get_dimension_by_name returns correct dimension."""
        dimension = Dimension(name="user_id", type=DimensionType.NUMBER)
        view = LookMLView(
            name="test_view",
            sql_table_name="test.table",
            dimensions=[dimension],
        )

        found_dimension = view.get_dimension_by_name("user_id")

        assert found_dimension is not None
        assert found_dimension.name == "user_id"

    def test_lookml_view_get_dimension_by_name_not_found(self):
        """Test get_dimension_by_name returns None when not found."""
        dimension = Dimension(name="user_id", type=DimensionType.NUMBER)
        view = LookMLView(
            name="test_view",
            sql_table_name="test.table",
            dimensions=[dimension],
        )

        found_dimension = view.get_dimension_by_name("nonexistent")

        assert found_dimension is None

    def test_lookml_view_get_measure_by_name_found(self):
        """Test get_measure_by_name returns correct measure."""
        measure = Measure(name="total_count", type=MeasureType.COUNT)
        view = LookMLView(
            name="test_view",
            sql_table_name="test.table",
            measures=[measure],
        )

        found_measure = view.get_measure_by_name("total_count")

        assert found_measure is not None
        assert found_measure.name == "total_count"

    def test_lookml_view_get_measure_by_name_not_found(self):
        """Test get_measure_by_name returns None when not found."""
        measure = Measure(name="total_count", type=MeasureType.COUNT)
        view = LookMLView(
            name="test_view",
            sql_table_name="test.table",
            measures=[measure],
        )

        found_measure = view.get_measure_by_name("nonexistent")

        assert found_measure is None

    def test_lookml_view_to_dict_basic(self):
        """Test basic to_dict conversion with required fields only."""
        view = LookMLView(name="users", sql_table_name="analytics.users")

        result = view.to_dict()

        expected = {
            "view": [
                {
                    "name": "users",
                    "sql_table_name": "analytics.users",
                }
            ]
        }
        assert result == expected

    def test_lookml_view_to_dict_with_optional_fields(self):
        """Test to_dict conversion with optional fields."""
        view = LookMLView(
            name="users",
            sql_table_name="analytics.users",
            connection="bigquery_conn",
            description="User data",
            drill_fields=["id", "name"],
        )

        result = view.to_dict()

        expected = {
            "view": [
                {
                    "name": "users",
                    "sql_table_name": "analytics.users",
                    "connection": "bigquery_conn",
                    "description": "User data",
                    "drill_fields": "['id', 'name']",
                }
            ]
        }
        assert result == expected

    def test_lookml_view_to_dict_with_fields(self):
        """Test to_dict conversion with dimensions, dimension groups, and measures."""
        dimension, dim_group, measure = self.create_sample_fields()

        view = LookMLView(
            name="users",
            sql_table_name="analytics.users",
            dimensions=[dimension],
            dimension_groups=[dim_group],
            measures=[measure],
        )

        result = view.to_dict()

        expected = {
            "view": [
                {
                    "name": "users",
                    "sql_table_name": "analytics.users",
                    "dimension": [
                        {
                            "name": "id",
                            "type": "number",
                            "primary_key": "yes",
                        }
                    ],
                    "dimension_group": [
                        {
                            "name": "created",
                            "type": "time",
                        }
                    ],
                    "measure": [
                        {
                            "name": "count",
                            "type": "count",
                        }
                    ],
                }
            ]
        }
        assert result == expected

    def test_lookml_view_to_dict_empty_field_lists(self):
        """Test to_dict omits empty field lists."""
        view = LookMLView(
            name="users",
            sql_table_name="analytics.users",
            dimensions=[],  # Empty lists should be omitted
            dimension_groups=[],
            measures=[],
        )

        result = view.to_dict()

        expected = {
            "view": [
                {
                    "name": "users",
                    "sql_table_name": "analytics.users",
                }
            ]
        }
        assert result == expected


class TestLookMLProject:
    """Test LookMLProject model and serialization logic."""

    def create_sample_views(self) -> list[LookMLView]:
        """Helper to create sample views for testing."""
        dimension1 = Dimension(name="id", type=DimensionType.NUMBER, primary_key=True)
        measure1 = Measure(name="count", type=MeasureType.COUNT)

        view1 = LookMLView(
            name="users",
            sql_table_name="analytics.users",
            dimensions=[dimension1],
            measures=[measure1],
        )

        dimension2 = Dimension(name="order_id", type=DimensionType.NUMBER)
        dim_group2 = DimensionGroup(name="created", type=DimensionGroupType.TIME)

        view2 = LookMLView(
            name="orders",
            sql_table_name="sales.orders",
            dimensions=[dimension2],
            dimension_groups=[dim_group2],
        )

        return [view1, view2]

    def test_empty_lookml_project(self):
        """Test creation of empty LookML project."""
        project = LookMLProject()

        assert len(project.views) == 0

    def test_lookml_project_with_initial_views(self):
        """Test creation with initial views."""
        views = self.create_sample_views()
        project = LookMLProject(views=views)

        assert len(project.views) == 2
        assert project.views[0].name == "users"
        assert project.views[1].name == "orders"

    def test_lookml_project_add_view(self):
        """Test add_view method."""
        project = LookMLProject()
        view = LookMLView(name="test_view", sql_table_name="test.table")

        project.add_view(view)

        assert len(project.views) == 1
        assert project.views[0].name == "test_view"

    def test_lookml_project_get_view_by_name_found(self):
        """Test get_view_by_name returns correct view."""
        views = self.create_sample_views()
        project = LookMLProject(views=views)

        found_view = project.get_view_by_name("users")

        assert found_view is not None
        assert found_view.name == "users"
        assert found_view.sql_table_name == "analytics.users"

    def test_lookml_project_get_view_by_name_not_found(self):
        """Test get_view_by_name returns None when not found."""
        views = self.create_sample_views()
        project = LookMLProject(views=views)

        found_view = project.get_view_by_name("nonexistent")

        assert found_view is None

    def test_lookml_project_to_dict_empty(self):
        """Test to_dict returns empty dict for project with no views."""
        project = LookMLProject()

        result = project.to_dict()

        assert result == {}

    def test_lookml_project_to_dict_with_views(self):
        """Test to_dict conversion with multiple views."""
        views = self.create_sample_views()
        project = LookMLProject(views=views)

        result = project.to_dict()

        # Should have all view entries in a single "view" array
        assert "view" in result
        assert isinstance(result["view"], list)
        assert len(result["view"]) == 2

        # Check that each view is properly serialized
        view_names = [view_entry["name"] for view_entry in result["view"]]
        assert "users" in view_names
        assert "orders" in view_names

        # Check structure of first view
        users_view = next(v for v in result["view"] if v["name"] == "users")
        assert users_view["sql_table_name"] == "analytics.users"
        assert "dimension" in users_view
        assert "measure" in users_view
        assert len(users_view["dimension"]) == 1
        assert len(users_view["measure"]) == 1

        # Check structure of second view
        orders_view = next(v for v in result["view"] if v["name"] == "orders")
        assert orders_view["sql_table_name"] == "sales.orders"
        assert "dimension" in orders_view
        assert "dimension_group" in orders_view
        assert len(orders_view["dimension"]) == 1
        assert len(orders_view["dimension_group"]) == 1

    def test_lookml_project_to_dict_with_single_view(self):
        """Test to_dict conversion with single view."""
        dimension = Dimension(name="id", type=DimensionType.NUMBER)
        view = LookMLView(
            name="single_view",
            sql_table_name="test.table",
            dimensions=[dimension],
        )
        project = LookMLProject(views=[view])

        result = project.to_dict()

        expected = {
            "view": [
                {
                    "name": "single_view",
                    "sql_table_name": "test.table",
                    "dimension": [
                        {
                            "name": "id",
                            "type": "number",
                        }
                    ],
                }
            ]
        }
        assert result == expected


class TestEnumValues:
    """Test enum value constraints and conversions."""

    def test_dimension_type_enum_values(self):
        """Test DimensionType enum has expected values."""
        assert DimensionType.STRING == "string"
        assert DimensionType.NUMBER == "number"
        assert DimensionType.YESNO == "yesno"
        assert DimensionType.TIER == "tier"
        assert DimensionType.LOCATION == "location"
        assert DimensionType.ZIPCODE == "zipcode"

    def test_dimension_group_type_enum_values(self):
        """Test DimensionGroupType enum has expected values."""
        assert DimensionGroupType.TIME == "time"
        assert DimensionGroupType.DURATION == "duration"

    def test_measure_type_enum_values(self):
        """Test MeasureType enum has expected values."""
        assert MeasureType.COUNT == "count"
        assert MeasureType.COUNT_DISTINCT == "count_distinct"
        assert MeasureType.SUM == "sum"
        assert MeasureType.AVERAGE == "average"
        assert MeasureType.MIN == "min"
        assert MeasureType.MAX == "max"
        assert MeasureType.MEDIAN == "median"
        assert MeasureType.PERCENTILE == "percentile"
        assert MeasureType.LIST == "list"
        assert MeasureType.NUMBER == "number"

    def test_invalid_enum_values_rejected(self):
        """Test that invalid enum values are rejected."""
        with pytest.raises(ValidationError):
            Dimension(name="test", type="invalid_type")

        with pytest.raises(ValidationError):
            DimensionGroup(name="test", type="invalid_type")

        with pytest.raises(ValidationError):
            Measure(name="test", type="invalid_type")
