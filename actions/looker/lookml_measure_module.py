"""
LookML Measure Module

This module generates a simple count measure for each LookML view,
matching the standard Looker LookML generator behavior.
"""

from typing import Any

from ..models.config import ConcordiaConfig
from ..models.metadata import TableMetadata


class LookMLMeasureGenerator:
    """Generates a simple count measure for LookML views."""

    def __init__(self, config: ConcordiaConfig):
        """
        Initialize the measure generator.

        Args:
            config: The loaded ConcordiaConfig object
        """
        self.config = config

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
