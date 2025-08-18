"""
Unit tests for lookml_measure_module.py.

Tests the LookMLMeasureGenerator class for measure generation logic,
including default measures, automatic measures, and custom measures.
"""

from actions.looker.lookml_measure_module import LookMLMeasureGenerator
from actions.models.metadata import ColumnMetadata


class TestLookMLMeasureGenerator:
    """Test cases for LookMLMeasureGenerator class."""

    def test_init(self, sample_config):
        """Test initialization of LookMLMeasureGenerator."""
        generator = LookMLMeasureGenerator(sample_config)

        assert generator.config == sample_config
        assert generator.model_rules == sample_config.model_rules
        assert generator.field_identifier is not None

    def test_generate_measures_for_view(self, sample_config, sample_table_metadata):
        """Test complete measure generation for a view."""
        generator = LookMLMeasureGenerator(sample_config)
        measures = generator.generate_measures_for_view(sample_table_metadata)

        # Should have at least default measures
        assert len(measures) > 0

        # Check that we have a count measure (from defaults)
        measure_names = []
        for measure in measures:
            measure_names.extend(measure.keys())

        assert "count" in measure_names

    def test_generate_default_measures_count(self, sample_config):
        """Test generation of default count measure."""
        generator = LookMLMeasureGenerator(sample_config)
        measures = generator._generate_default_measures()

        assert len(measures) == 1  # Only count is in defaults
        assert "count" in measures[0]

        count_measure = measures[0]["count"]
        assert count_measure["type"] == "count"
        assert count_measure["description"] == "Count of records"
        assert count_measure["drill_fields"] == ["detail*"]

    def test_generate_default_measures_count_distinct(self, sample_config):
        """Test generation of default count_distinct measure."""
        # Create a new config with count_distinct added to defaults
        modified_defaults = sample_config.model_rules.defaults.copy(update={"measures": ["count", "count_distinct"]})
        modified_model_rules = sample_config.model_rules.copy(update={"defaults": modified_defaults})
        modified_config = sample_config.copy(update={"model_rules": modified_model_rules})

        generator = LookMLMeasureGenerator(modified_config)
        measures = generator._generate_default_measures()

        assert len(measures) == 2

        measure_names = []
        for measure in measures:
            measure_names.extend(measure.keys())

        assert "count" in measure_names
        assert "count_distinct" in measure_names

    def test_generate_automatic_measures_skips_hidden_fields(self, sample_config):
        """Test that automatic measure generation skips hidden fields."""
        generator = LookMLMeasureGenerator(sample_config)

        # Test with primary key (should be skipped)
        pk_column = ColumnMetadata(name="user_pk", type="INTEGER", standardized_type="INTEGER")

        measures = generator._generate_automatic_measures(pk_column)
        assert len(measures) == 0

        # Test with foreign key (should be skipped)
        fk_column = ColumnMetadata(name="organization_fk", type="INTEGER", standardized_type="INTEGER")

        measures = generator._generate_automatic_measures(fk_column)
        assert len(measures) == 0

    def test_generate_automatic_measures_numeric_column(self, sample_config):
        """Test automatic measure generation for numeric columns."""
        generator = LookMLMeasureGenerator(sample_config)

        numeric_column = ColumnMetadata(name="age", type="INTEGER", standardized_type="INTEGER")

        measures = generator._generate_automatic_measures(numeric_column)

        # Should generate numeric measures (sum, avg, min, max)
        assert len(measures) == 4

        measure_names = []
        for measure in measures:
            measure_names.extend(measure.keys())

        assert "total_age" in measure_names
        assert "avg_age" in measure_names
        assert "min_age" in measure_names
        assert "max_age" in measure_names

    def test_generate_automatic_measures_amount_column(self, sample_config):
        """Test automatic measure generation for amount columns."""
        generator = LookMLMeasureGenerator(sample_config)

        amount_column = ColumnMetadata(name="order_amount", type="NUMERIC", standardized_type="NUMERIC")

        measures = generator._generate_automatic_measures(amount_column)

        # Should generate both numeric measures and amount measures
        assert len(measures) > 4  # More than just numeric measures

        measure_names = []
        for measure in measures:
            measure_names.extend(measure.keys())

        # Check for amount-specific measures with currency formatting
        assert "total_order_amount" in measure_names
        assert "avg_order_amount" in measure_names

    def test_generate_numeric_measures(self, sample_config):
        """Test generation of standard numeric measures."""
        generator = LookMLMeasureGenerator(sample_config)

        column = ColumnMetadata(name="score", type="INTEGER", standardized_type="INTEGER")

        measures = generator._generate_numeric_measures(column)

        assert len(measures) == 4

        # Check total measure
        total_measure = next(m for m in measures if "total_score" in m)
        assert total_measure["total_score"]["type"] == "sum"
        assert total_measure["total_score"]["sql"] == "${TABLE}.score"
        assert "Total score" in total_measure["total_score"]["description"]

        # Check average measure
        avg_measure = next(m for m in measures if "avg_score" in m)
        assert avg_measure["avg_score"]["type"] == "average"

        # Check min measure
        min_measure = next(m for m in measures if "min_score" in m)
        assert min_measure["min_score"]["type"] == "min"

        # Check max measure
        max_measure = next(m for m in measures if "max_score" in m)
        assert max_measure["max_score"]["type"] == "max"

    def test_generate_amount_measures(self, sample_config):
        """Test generation of amount/currency measures."""
        generator = LookMLMeasureGenerator(sample_config)

        column = ColumnMetadata(name="revenue", type="NUMERIC", standardized_type="NUMERIC")

        measures = generator._generate_amount_measures(column)

        assert len(measures) == 2

        # Check total amount with currency formatting
        total_measure = next(m for m in measures if "total_revenue" in m)
        assert total_measure["total_revenue"]["type"] == "sum"
        assert total_measure["total_revenue"]["value_format_name"] == "usd"

        # Check average amount with currency formatting
        avg_measure = next(m for m in measures if "avg_revenue" in m)
        assert avg_measure["avg_revenue"]["type"] == "average"
        assert avg_measure["avg_revenue"]["value_format_name"] == "usd"

    def test_generate_count_measures(self, sample_config):
        """Test generation of count-type measures."""
        generator = LookMLMeasureGenerator(sample_config)

        column = ColumnMetadata(name="order_count", type="INTEGER", standardized_type="INTEGER")

        measures = generator._generate_count_measures(column)

        assert len(measures) == 1

        total_measure = measures[0]["total_order_count"]
        assert total_measure["type"] == "sum"
        assert total_measure["value_format_name"] == "decimal_0"
        assert "Total order count" in total_measure["description"]

    def test_generate_ratio_measures(self, sample_config):
        """Test generation of ratio/percentage measures."""
        generator = LookMLMeasureGenerator(sample_config)

        column = ColumnMetadata(name="conversion_rate", type="FLOAT", standardized_type="FLOAT")

        measures = generator._generate_ratio_measures(column)

        assert len(measures) == 1

        avg_measure = measures[0]["avg_conversion_rate"]
        assert avg_measure["type"] == "average"
        assert avg_measure["value_format_name"] == "percent_2"
        assert "Average conversion rate" in avg_measure["description"]

    def test_generate_custom_measure_basic(self, sample_config):
        """Test generation of custom measure with basic configuration."""
        generator = LookMLMeasureGenerator(sample_config)

        measure_config = {
            "name": "custom_metric",
            "type": "sum",
            "sql": "${TABLE}.some_field * 2",
        }

        result = generator.generate_custom_measure(measure_config)

        assert "custom_metric" in result
        measure = result["custom_metric"]
        assert measure["type"] == "sum"
        assert measure["sql"] == "${TABLE}.some_field * 2"

    def test_generate_custom_measure_with_optional_properties(self, sample_config):
        """Test generation of custom measure with optional properties."""
        generator = LookMLMeasureGenerator(sample_config)

        measure_config = {
            "name": "complex_metric",
            "type": "number",
            "sql": "SUM(${TABLE}.field1) / COUNT(*)",
            "description": "A complex calculated measure",
            "value_format_name": "decimal_2",
            "drill_fields": ["field1", "field2"],
        }

        result = generator.generate_custom_measure(measure_config)

        assert "complex_metric" in result
        measure = result["complex_metric"]
        assert measure["type"] == "number"
        assert measure["description"] == "A complex calculated measure"
        assert measure["value_format_name"] == "decimal_2"
        assert measure["drill_fields"] == ["field1", "field2"]

    def test_generate_ratio_measure_default_name(self, sample_config):
        """Test ratio measure generation with default naming."""
        generator = LookMLMeasureGenerator(sample_config)

        result = generator.generate_ratio_measure("conversions", "visits")

        assert "conversions_to_visits_ratio" in result
        measure = result["conversions_to_visits_ratio"]
        assert measure["type"] == "number"
        assert "SAFE_DIVIDE" in measure["sql"]
        assert "conversions" in measure["sql"]
        assert "visits" in measure["sql"]
        assert measure["value_format_name"] == "decimal_4"

    def test_generate_ratio_measure_custom_name(self, sample_config):
        """Test ratio measure generation with custom name."""
        generator = LookMLMeasureGenerator(sample_config)

        result = generator.generate_ratio_measure("sales", "leads", measure_name="conversion_ratio")

        assert "conversion_ratio" in result
        measure = result["conversion_ratio"]
        assert "sales" in measure["sql"]
        assert "leads" in measure["sql"]

    def test_generate_cohort_measure(self, sample_config):
        """Test cohort measure generation."""
        generator = LookMLMeasureGenerator(sample_config)

        cohort_periods = ["month", "quarter"]
        measures = generator.generate_cohort_measure("signup_date", "revenue", cohort_periods)

        assert len(measures) == 2

        # Check month cohort measure
        month_measure = next(m for m in measures if "revenue_cohort_month" in m)
        assert month_measure["revenue_cohort_month"]["type"] == "sum"
        assert "signup_date_month" in month_measure["revenue_cohort_month"]["filters"]

        # Check quarter cohort measure
        quarter_measure = next(m for m in measures if "revenue_cohort_quarter" in m)
        assert quarter_measure["revenue_cohort_quarter"]["type"] == "sum"

    def test_is_numeric_column(self, sample_config):
        """Test numeric column identification."""
        generator = LookMLMeasureGenerator(sample_config)

        # Test numeric types
        assert (
            generator._is_numeric_column(ColumnMetadata(name="test", type="INTEGER", standardized_type="INTEGER"))
            is True
        )
        assert (
            generator._is_numeric_column(ColumnMetadata(name="test", type="INT64", standardized_type="INT64")) is True
        )
        assert (
            generator._is_numeric_column(ColumnMetadata(name="test", type="FLOAT", standardized_type="FLOAT64")) is True
        )
        assert (
            generator._is_numeric_column(ColumnMetadata(name="test", type="FLOAT64", standardized_type="FLOAT64"))
            is True
        )
        assert (
            generator._is_numeric_column(ColumnMetadata(name="test", type="NUMERIC", standardized_type="NUMERIC"))
            is True
        )
        assert (
            generator._is_numeric_column(ColumnMetadata(name="test", type="BIGNUMERIC", standardized_type="BIGNUMERIC"))
            is True
        )

        # Test non-numeric types
        assert (
            generator._is_numeric_column(ColumnMetadata(name="test", type="STRING", standardized_type="STRING"))
            is False
        )
        assert (
            generator._is_numeric_column(ColumnMetadata(name="test", type="BOOLEAN", standardized_type="BOOL")) is False
        )
        assert generator._is_numeric_column(ColumnMetadata(name="test", type="DATE", standardized_type="DATE")) is False

    def test_is_amount_column(self, sample_config):
        """Test amount column identification."""
        generator = LookMLMeasureGenerator(sample_config)

        # Test amount column names
        assert generator._is_amount_column("order_amount") is True
        assert generator._is_amount_column("product_price") is True
        assert generator._is_amount_column("shipping_cost") is True
        assert generator._is_amount_column("account_value") is True
        assert generator._is_amount_column("monthly_revenue") is True
        assert generator._is_amount_column("total_sales") is True
        assert generator._is_amount_column("processing_fee") is True
        assert generator._is_amount_column("grand_total") is True

        # Test non-amount column names
        assert generator._is_amount_column("user_id") is False
        assert generator._is_amount_column("email") is False
        assert generator._is_amount_column("created_at") is False

    def test_is_count_column(self, sample_config):
        """Test count column identification."""
        generator = LookMLMeasureGenerator(sample_config)

        # Test count column names
        assert generator._is_count_column("order_count") is True
        assert generator._is_count_column("item_quantity") is True
        assert generator._is_count_column("qty_ordered") is True
        assert generator._is_count_column("number_of_visits") is True
        assert generator._is_count_column("num_employees") is True

        # Test non-count column names
        assert generator._is_count_column("user_id") is False
        assert generator._is_count_column("email") is False
        assert generator._is_count_column("order_amount") is False

    def test_is_ratio_column(self, sample_config):
        """Test ratio column identification."""
        generator = LookMLMeasureGenerator(sample_config)

        # Test ratio column names
        assert generator._is_ratio_column("conversion_ratio") is True
        assert generator._is_ratio_column("click_rate") is True
        assert generator._is_ratio_column("success_percent") is True
        assert generator._is_ratio_column("failure_percentage") is True
        assert generator._is_ratio_column("discount_pct") is True

        # Test non-ratio column names
        assert generator._is_ratio_column("user_id") is False
        assert generator._is_ratio_column("email") is False
        assert generator._is_ratio_column("order_amount") is False

    def test_field_identification_methods(self, sample_config):
        """Test field identification helper methods."""
        generator = LookMLMeasureGenerator(sample_config)

        # Test hidden field identification
        assert generator._should_hide_field("user_pk") is True
        assert generator._should_hide_field("organization_fk") is True
        assert generator._should_hide_field("email") is False

        # Test primary key identification
        assert generator._is_primary_key("user_pk") is True
        assert generator._is_primary_key("id") is True
        assert generator._is_primary_key("email") is False

        # Test foreign key identification
        assert generator._is_foreign_key("organization_fk") is True
        assert generator._is_foreign_key("user_pk") is False
        assert generator._is_foreign_key("email") is False
