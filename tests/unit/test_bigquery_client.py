"""
Unit tests for the BigQuery client module.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from actions.looker.bigquery_client import BigQueryClient, ErrorTracker, TableInfo


class TestErrorTracker:
    """Test error tracker functionality."""

    def test_error_tracker_init(self):
        """Test ErrorTracker initialization."""
        tracker = ErrorTracker()

        assert len(tracker.dataset_errors) == 0
        assert len(tracker.table_errors) == 0
        assert len(tracker.permission_errors) == 0
        assert len(tracker.not_found_errors) == 0
        assert len(tracker.connection_errors) == 0
        assert len(tracker.unexpected_errors) == 0

    def test_add_dataset_error_permission(self):
        """Test adding permission dataset error."""
        tracker = ErrorTracker()
        error = ValueError("Test error")

        tracker.add_dataset_error("test_dataset", error, "permission")

        assert len(tracker.permission_errors) == 1
        assert tracker.permission_errors[0]["dataset_id"] == "test_dataset"
        assert tracker.permission_errors[0]["error"] == "Test error"
        assert tracker.permission_errors[0]["error_type"] == "permission"
        assert tracker.permission_errors[0]["exception_type"] == "ValueError"

    def test_add_dataset_error_unexpected(self):
        """Test adding unexpected dataset error."""
        tracker = ErrorTracker()
        error = ValueError("Test error")

        tracker.add_dataset_error("test_dataset", error, "unexpected")

        assert len(tracker.dataset_errors) == 1
        assert tracker.dataset_errors[0]["dataset_id"] == "test_dataset"
        assert tracker.dataset_errors[0]["error"] == "Test error"
        assert tracker.dataset_errors[0]["error_type"] == "unexpected"
        assert tracker.dataset_errors[0]["exception_type"] == "ValueError"

    def test_add_dataset_error_not_found(self):
        """Test adding not found dataset error."""
        tracker = ErrorTracker()
        error = FileNotFoundError("Dataset not found")

        tracker.add_dataset_error("test_dataset", error, "not_found")

        assert len(tracker.not_found_errors) == 1
        assert tracker.not_found_errors[0]["dataset_id"] == "test_dataset"
        assert tracker.not_found_errors[0]["error"] == "Dataset not found"
        assert tracker.not_found_errors[0]["error_type"] == "not_found"
        assert tracker.not_found_errors[0]["exception_type"] == "FileNotFoundError"

    def test_add_dataset_error_connection(self):
        """Test adding connection dataset error."""
        tracker = ErrorTracker()
        error = ConnectionError("Connection failed")

        tracker.add_dataset_error("test_dataset", error, "connection")

        assert len(tracker.connection_errors) == 1
        assert tracker.connection_errors[0]["dataset_id"] == "test_dataset"
        assert tracker.connection_errors[0]["error"] == "Connection failed"
        assert tracker.connection_errors[0]["error_type"] == "connection"
        assert tracker.connection_errors[0]["exception_type"] == "ConnectionError"


class TestTableInfo:
    """Test table info functionality."""

    def test_table_info_init(self):
        """Test TableInfo initialization."""
        table_info = TableInfo(
            dataset_id="test_dataset", table_id="users", description="User table"
        )

        assert table_info.dataset_id == "test_dataset"
        assert table_info.table_id == "users"
        assert table_info.full_table_id == "test_dataset.users"
        assert table_info.description == "User table"
        assert len(table_info.columns) == 0

    def test_table_info_no_description(self):
        """Test TableInfo without description."""
        table_info = TableInfo(dataset_id="test_dataset", table_id="users")

        assert table_info.dataset_id == "test_dataset"
        assert table_info.table_id == "users"
        assert table_info.full_table_id == "test_dataset.users"
        assert table_info.description is None

    def test_add_column(self):
        """Test adding columns to table info."""
        table_info = TableInfo("test_dataset", "users")

        table_info.add_column("id", "INTEGER", "REQUIRED", "Primary key")
        table_info.add_column("email", "STRING")

        assert len(table_info.columns) == 2

        # Check first column
        assert table_info.columns[0]["name"] == "id"
        assert table_info.columns[0]["type"] == "INTEGER"
        assert table_info.columns[0]["mode"] == "REQUIRED"
        assert table_info.columns[0]["description"] == "Primary key"

        # Check second column (defaults)
        assert table_info.columns[1]["name"] == "email"
        assert table_info.columns[1]["type"] == "STRING"
        assert table_info.columns[1]["mode"] == "NULLABLE"
        assert table_info.columns[1]["description"] is None


class TestBigQueryClient:
    """Test BigQuery client functionality."""

    @patch("actions.looker.bigquery_client.bigquery.Client")
    def test_bigquery_client_init(self, mock_client_class):
        """Test BigQueryClient initialization."""
        mock_credentials = Mock()
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        client = BigQueryClient(
            credentials=mock_credentials, project_id="test_project", location="US"
        )

        assert client.project_id == "test_project"
        assert client.location == "US"
        mock_client_class.assert_called_once()

    @patch("actions.looker.bigquery_client.bigquery.Client")
    def test_bigquery_client_init_no_location(self, mock_client_class):
        """Test BigQueryClient initialization without location."""
        mock_credentials = Mock()
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        client = BigQueryClient(credentials=mock_credentials, project_id="test_project")

        assert client.project_id == "test_project"
        assert client.location is None

    @patch("actions.looker.bigquery_client.bigquery.Client")
    def test_bigquery_client_init_with_config(self, mock_client_class):
        """Test BigQueryClient initialization with config."""
        mock_credentials = Mock()
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        config = {"model_rules": {"naming_conventions": {"primary_key_suffix": "_pk"}}}

        client = BigQueryClient(
            credentials=mock_credentials, project_id="test_project", config=config
        )

        assert client.project_id == "test_project"
        assert client.config == config
