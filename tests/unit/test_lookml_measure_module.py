"""
Unit tests for lookml_measure_module.py.

Tests the LookMLMeasureGenerator class for simple count measure generation.
"""

from actions.looker.lookml_measure_module import LookMLMeasureGenerator


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

        # Should return exactly one measure (count)
        assert len(measures) == 1
        assert "count" in measures[0]

        # Verify the count measure structure
        count_measure = measures[0]["count"]
        assert count_measure["type"] == "count"
        assert count_measure["description"] == "Count of records"
        assert count_measure["drill_fields"] == ["detail*"]
