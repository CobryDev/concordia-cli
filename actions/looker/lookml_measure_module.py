"""
LookML Measure Module

This module generates a simple count measure for each LookML view,
matching the standard Looker LookML generator behavior.
"""

from typing import Any

from ..models.config import ConcordiaConfig
from ..models.metadata import TableMetadata
from .field_utils import FieldIdentifier


class LookMLMeasureGenerator:
    """Generates a simple count measure for LookML views."""

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
        Generate a count measure for a view.

        Args:
            table_metadata: TableMetadata object from MetadataExtractor

        Returns:
            List containing a single count measure dictionary
        """
        return [
            {
                "count": {
                    "type": "count",
                    "description": "Count of records",
                    "drill_fields": ["detail*"],
                }
            }
        ]
