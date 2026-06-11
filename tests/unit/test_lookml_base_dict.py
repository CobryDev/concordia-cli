"""Unit tests for BigQuery metadata extraction."""

from unittest.mock import Mock, patch

import pandas as pd
import pytest

from actions.looker.lookml_base_dict import MetadataExtractor


def create_extractor(table_types: list[str] | None = None) -> MetadataExtractor:
    """Create a metadata extractor with mocked credentials."""
    return MetadataExtractor(
        credentials=Mock(),
        project_id="test-project",
        location="US",
        table_types=table_types,
    )


class TestMetadataExtractorTableTypes:
    """Test BigQuery table type filtering."""

    def test_default_table_types_include_base_tables_only(self):
        """Test default table type filter preserves existing behavior."""
        extractor = create_extractor()

        assert extractor.table_types == ["BASE TABLE"]
        assert extractor._table_type_filter_sql() == "'BASE TABLE'"

    def test_table_types_are_normalized_and_deduplicated(self):
        """Test configured table types are normalized before SQL generation."""
        extractor = create_extractor([" base table ", "view", "VIEW", "materialized view"])

        assert extractor.table_types == ["BASE TABLE", "VIEW", "MATERIALIZED VIEW"]
        assert extractor._table_type_filter_sql() == "'BASE TABLE', 'VIEW', 'MATERIALIZED VIEW'"

    def test_empty_table_types_are_rejected(self):
        """Test an explicitly empty table type list does not fall back silently."""
        with pytest.raises(ValueError, match="At least one BigQuery table type"):
            create_extractor([])

    def test_blank_table_types_are_rejected(self):
        """Test blank table type values are rejected."""
        with pytest.raises(ValueError, match="Table types cannot be empty"):
            create_extractor(["BASE TABLE", "  "])

    def test_non_string_table_types_are_rejected(self):
        """Test non-string table type values are rejected."""
        with pytest.raises(ValueError, match="Table types must be strings"):
            create_extractor(["BASE TABLE", 123])  # type: ignore[list-item]

    def test_unknown_table_types_are_rejected(self):
        """Test unsupported table type values are rejected."""
        with pytest.raises(ValueError, match="Invalid BigQuery table type 'TABLE'"):
            create_extractor(["TABLE"])


class TestMetadataExtractorQueries:
    """Test generated INFORMATION_SCHEMA queries."""

    @patch("actions.looker.lookml_base_dict.pandas_gbq.read_gbq")
    def test_get_table_metadata_filters_configured_table_types(self, mock_read_gbq):
        """Test table metadata query includes configured table types."""
        mock_read_gbq.return_value = pd.DataFrame()
        extractor = create_extractor(["BASE TABLE", "VIEW"])

        extractor.get_table_metadata(["analytics"])

        query = mock_read_gbq.call_args.args[0]
        assert "FROM `analytics`.INFORMATION_SCHEMA.TABLES" in query
        assert "WHERE table_type IN ('BASE TABLE', 'VIEW')" in query
        assert mock_read_gbq.call_args.kwargs["project_id"] == "test-project"
        assert mock_read_gbq.call_args.kwargs["location"] == "US"

    @patch("actions.looker.lookml_base_dict.pandas_gbq.read_gbq")
    def test_get_table_metadata_validates_dataset_ids_before_querying(self, mock_read_gbq):
        """Test unsafe dataset identifiers are rejected before query execution."""
        extractor = create_extractor(["BASE TABLE", "VIEW"])

        with pytest.raises(ValueError, match="must not contain quotes or dots"):
            extractor.get_table_metadata(["project.dataset"])

        mock_read_gbq.assert_not_called()


class TestMetadataWrangling:
    """Test conversion from BigQuery metadata frames to models."""

    def test_wrangle_metadata_preserves_view_metadata(self):
        """Test views survive wrangling with their table type and DDL."""
        extractor = create_extractor(["BASE TABLE", "VIEW"])
        tables_df = pd.DataFrame(
            [
                {
                    "project_id": "test-project",
                    "dataset_id": "analytics",
                    "table_id": "users",
                    "table_type": "BASE TABLE",
                    "creation_ddl": "CREATE TABLE `test-project.analytics.users`",
                    "table_description": "Users table",
                },
                {
                    "project_id": "test-project",
                    "dataset_id": "analytics",
                    "table_id": "customer_summary",
                    "table_type": "VIEW",
                    "creation_ddl": "CREATE VIEW `test-project.analytics.customer_summary` AS SELECT 1",
                    "table_description": "Customer summary view",
                },
            ]
        )
        columns_df = pd.DataFrame(
            [
                {
                    "project_id": "test-project",
                    "dataset_id": "analytics",
                    "table_id": "users",
                    "column_name": "user_id",
                    "ordinal_position": 1,
                    "is_nullable": "NO",
                    "data_type": "STRING",
                    "column_description": "User ID",
                },
                {
                    "project_id": "test-project",
                    "dataset_id": "analytics",
                    "table_id": "customer_summary",
                    "column_name": "customer_count",
                    "ordinal_position": 1,
                    "is_nullable": "YES",
                    "data_type": "INT64",
                    "column_description": "Number of customers",
                },
            ]
        )

        collection = extractor.wrangle_metadata(tables_df, columns_df, pd.DataFrame())

        assert collection.table_count() == 2
        view = collection.get_table("analytics.customer_summary")
        assert view is not None
        assert view.table_type == "VIEW"
        assert view.creation_ddl == "CREATE VIEW `test-project.analytics.customer_summary` AS SELECT 1"
        assert view.table_description == "Customer summary view"
        assert view.columns[0].name == "customer_count"
        assert view.columns[0].standardized_type == "INT64"
