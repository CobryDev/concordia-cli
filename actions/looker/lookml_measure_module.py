"""
LookML Measure Module

This module generates LookML measures as Python dictionaries following the droughty pattern.
It handles automatic measure generation based on column types and naming conventions.
"""

from typing import Any, Optional

from ..models.config import ConcordiaConfig
from ..models.metadata import ColumnMetadata, TableMetadata
from .field_utils import FieldIdentifier


class LookMLMeasureGenerator:
    """Generates LookML measures as Python dictionaries."""

    def __init__(self, config: ConcordiaConfig):
        """
        Initialize the measure generator.

        Args:
            config: The loaded ConcordiaConfig object
        """
        self.config = config
        self.model_rules = config.model_rules
        self.field_identifier = FieldIdentifier(self.model_rules)

    def generate_measures_for_view(self, table_metadata: TableMetadata) -> list[dict[str, Any]]:
        """
        Generate all measures for a view based on table metadata.

        Args:
            table_metadata: TableMetadata object from MetadataExtractor

        Returns:
            List of measure dictionaries
        """
        measures: list[dict[str, Any]] = []

        # Generate default measures (like count)
        default_measures = self._generate_default_measures()
        measures.extend(default_measures)

        # Generate automatic measures based on column types
        for column in table_metadata.columns:
            auto_measures = self._generate_automatic_measures(column)
            measures.extend(auto_measures)

        return measures

    def _generate_default_measures(self) -> list[dict[str, Any]]:
        """Generate default measures based on configuration."""
        measures: list[dict[str, Any]] = []
        default_measures = self.model_rules.defaults.measures

        for measure_type in default_measures:
            if measure_type == "count":
                measures.append(
                    {
                        "count": {
                            "type": "count",
                            "description": "Count of records",
                            "drill_fields": ["detail*"],
                        }
                    }
                )
            elif measure_type == "count_distinct":
                measures.append(
                    {
                        "count_distinct": {
                            "type": "count_distinct",
                            # This should be dynamic based on primary key
                            "sql": "${TABLE}.id",
                            "description": "Count of distinct records",
                        }
                    }
                )

        return measures

    def _generate_automatic_measures(self, column: ColumnMetadata) -> list[dict[str, Any]]:
        """
        Generate automatic measures based on column type and naming conventions.

        Args:
            column: ColumnMetadata object

        Returns:
            List of measure dictionaries
        """
        measures: list[dict[str, Any]] = []
        column_name = column.name

        # Skip hidden fields and primary/foreign keys
        if (
            self._should_hide_field(column_name)
            or self._is_primary_key(column_name)
            or self._is_foreign_key(column_name)
        ):
            return measures

        # Generate measures for numeric columns
        if self._is_numeric_column(column):
            measures.extend(self._generate_numeric_measures(column))

        # Generate measures for amount/currency columns
        if self._is_amount_column(column_name):
            measures.extend(self._generate_amount_measures(column))

        # Generate measures for count columns
        if self._is_count_column(column_name):
            measures.extend(self._generate_count_measures(column))

        # Generate measures for ratio/percentage columns
        if self._is_ratio_column(column_name):
            measures.extend(self._generate_ratio_measures(column))

        return measures

    def _generate_numeric_measures(self, column: ColumnMetadata) -> list[dict[str, Any]]:
        """Generate standard numeric measures (sum, average, min, max)."""
        measures: list[dict[str, Any]] = []
        column_name = column.name

        # Sum measure
        measures.append(
            {
                f"total_{column_name}": {
                    "type": "sum",
                    "sql": f"${{TABLE}}.{column_name}",
                    "description": f"Total {column_name.replace('_', ' ')}",
                }
            }
        )

        # Average measure
        measures.append(
            {
                f"avg_{column_name}": {
                    "type": "average",
                    "sql": f"${{TABLE}}.{column_name}",
                    "description": f"Average {column_name.replace('_', ' ')}",
                }
            }
        )

        # Min measure
        measures.append(
            {
                f"min_{column_name}": {
                    "type": "min",
                    "sql": f"${{TABLE}}.{column_name}",
                    "description": f"Minimum {column_name.replace('_', ' ')}",
                }
            }
        )

        # Max measure
        measures.append(
            {
                f"max_{column_name}": {
                    "type": "max",
                    "sql": f"${{TABLE}}.{column_name}",
                    "description": f"Maximum {column_name.replace('_', ' ')}",
                }
            }
        )

        return measures

    def _generate_amount_measures(self, column: ColumnMetadata) -> list[dict[str, Any]]:
        """Generate measures for amount/currency columns with proper formatting."""
        measures: list[dict[str, Any]] = []
        column_name = column.name

        # Total amount with currency formatting
        measures.append(
            {
                f"total_{column_name}": {
                    "type": "sum",
                    "sql": f"${{TABLE}}.{column_name}",
                    "description": f"Total {column_name.replace('_', ' ')}",
                    "value_format_name": "usd",
                }
            }
        )

        # Average amount
        measures.append(
            {
                f"avg_{column_name}": {
                    "type": "average",
                    "sql": f"${{TABLE}}.{column_name}",
                    "description": f"Average {column_name.replace('_', ' ')}",
                    "value_format_name": "usd",
                }
            }
        )

        return measures

    def _generate_count_measures(self, column: ColumnMetadata) -> list[dict[str, Any]]:
        """Generate measures for count-type columns."""
        measures: list[dict[str, Any]] = []
        column_name = column.name

        # Total count
        measures.append(
            {
                f"total_{column_name}": {
                    "type": "sum",
                    "sql": f"${{TABLE}}.{column_name}",
                    "description": f"Total {column_name.replace('_', ' ')}",
                    "value_format_name": "decimal_0",
                }
            }
        )

        return measures

    def _generate_ratio_measures(self, column: ColumnMetadata) -> list[dict[str, Any]]:
        """Generate measures for ratio/percentage columns."""
        measures: list[dict[str, Any]] = []
        column_name = column.name

        # Average ratio as percentage
        measures.append(
            {
                f"avg_{column_name}": {
                    "type": "average",
                    "sql": f"${{TABLE}}.{column_name}",
                    "description": f"Average {column_name.replace('_', ' ')}",
                    "value_format_name": "percent_2",
                }
            }
        )

        return measures

    def generate_custom_measure(self, measure_config: dict[str, Any]) -> dict[str, Any]:
        """
        Generate a custom measure based on configuration.

        Args:
            measure_config: Configuration dictionary for the custom measure

        Returns:
            Dictionary containing the custom measure definition
        """
        measure_name = measure_config["name"]
        measure_dict = {measure_name: {"type": measure_config["type"], "sql": measure_config["sql"]}}

        # Add optional properties
        optional_props = [
            "description",
            "value_format",
            "value_format_name",
            "drill_fields",
            "filters",
        ]
        for prop in optional_props:
            if prop in measure_config:
                measure_dict[measure_name][prop] = measure_config[prop]

        return measure_dict

    def generate_ratio_measure(
        self,
        numerator_column: str,
        denominator_column: str,
        measure_name: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Generate a ratio measure between two columns.

        Args:
            numerator_column: Column name for numerator
            denominator_column: Column name for denominator
            measure_name: Optional custom name for the measure

        Returns:
            Dictionary containing the ratio measure definition
        """
        if not measure_name:
            measure_name = f"{numerator_column}_to_{denominator_column}_ratio"

        return {
            measure_name: {
                "type": "number",
                "sql": f"SAFE_DIVIDE(SUM(${{TABLE}}.{numerator_column}), SUM(${{TABLE}}.{denominator_column}))",
                "description": f"Ratio of {numerator_column} to {denominator_column}",
                "value_format_name": "decimal_4",
            }
        }

    def generate_cohort_measure(
        self, date_column: str, value_column: str, cohort_periods: list[str]
    ) -> list[dict[str, Any]]:
        """
        Generate cohort analysis measures.

        Args:
            date_column: Column name for the date dimension
            value_column: Column name for the value to analyze
            cohort_periods: List of time periods for cohort analysis

        Returns:
            List of measure dictionaries for cohort analysis
        """
        measures: list[dict[str, Any]] = []

        for period in cohort_periods:
            measure_name = f"{value_column}_cohort_{period}"
            measures.append(
                {
                    measure_name: {
                        "type": "sum",
                        "sql": f"${{TABLE}}.{value_column}",
                        "description": f"Cohort {value_column} for {period} period",
                        "filters": {f"{date_column}_{period}": "NOT NULL"},
                    }
                }
            )

        return measures

    def _is_numeric_column(self, column: ColumnMetadata) -> bool:
        """Check if a column is numeric and suitable for measures."""
        numeric_types = [
            "INTEGER",
            "INT64",
            "FLOAT",
            "FLOAT64",
            "NUMERIC",
            "BIGNUMERIC",
        ]
        return column.standardized_type in numeric_types

    def _is_amount_column(self, column_name: str) -> bool:
        """Check if a column represents an amount or currency value."""
        amount_indicators = [
            "amount",
            "price",
            "cost",
            "value",
            "revenue",
            "sales",
            "fee",
            "total",
        ]
        return any(indicator in column_name.lower() for indicator in amount_indicators)

    def _is_count_column(self, column_name: str) -> bool:
        """Check if a column represents a count value."""
        count_indicators = ["count", "quantity", "qty", "number_of", "num_"]
        return any(indicator in column_name.lower() for indicator in count_indicators)

    def _is_ratio_column(self, column_name: str) -> bool:
        """Check if a column represents a ratio or percentage."""
        ratio_indicators = ["ratio", "rate", "percent", "percentage", "pct"]
        return any(indicator in column_name.lower() for indicator in ratio_indicators)

    def _should_hide_field(self, field_name: str) -> bool:
        """Check if a field should be hidden based on configuration."""
        return self.field_identifier.should_hide_field(field_name)

    def _is_primary_key(self, field_name: str) -> bool:
        """Check if a field is a primary key based on naming conventions."""
        return self.field_identifier.is_primary_key(field_name)

    def _is_foreign_key(self, field_name: str) -> bool:
        """Check if a field is a foreign key based on naming conventions."""
        return self.field_identifier.is_foreign_key(field_name)
