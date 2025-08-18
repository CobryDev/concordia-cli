"""
Integration tests for the generate command.

Tests end-to-end LookML generation workflow with mocked BigQuery,
file I/O operations, and error handling.
"""

import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import click
import pytest
import yaml
from click.testing import CliRunner

from actions.looker.generate import generate_lookml
from main import cli


class TestGenerateCommandIntegration:
    """Integration tests for the generate command."""

    def setup_method(self):
        """Set up test environment for each test."""
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        self.runner = CliRunner()

        # Create sample concordia.yaml for testing
        self.create_sample_config()

    def teardown_method(self):
        """Clean up test environment after each test."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)

    def create_sample_config(self):
        """Create a sample concordia.yaml configuration file."""
        config = {
            "connection": {
                "project_id": "test-project",
                "location": "US",
                "datasets": ["test_dataset"],
            },
            "looker": {
                "project_path": "./looker_project/",
                "views_path": "views/generated_views.view.lkml",
                "connection": "test-bigquery-connection",
            },
            "model_rules": {
                "naming_conventions": {"pk_suffix": "_pk", "fk_suffix": "_fk"},
                "defaults": {
                    "measures": ["count"],
                    "hide_fields_by_suffix": ["_pk", "_fk"],
                },
                "type_mapping": [
                    {
                        "bq_type": "STRING",
                        "lookml_type": "dimension",
                        "lookml_params": {"type": "string"},
                    },
                    {
                        "bq_type": "INTEGER",
                        "lookml_type": "dimension",
                        "lookml_params": {"type": "number"},
                    },
                    {
                        "bq_type": "TIMESTAMP",
                        "lookml_type": "dimension_group",
                        "lookml_params": {
                            "type": "time",
                            "timeframes": "[raw, time, date, week, month, quarter, year]",
                        },
                    },
                ],
            },
        }

        with open("concordia.yaml", "w") as f:
            yaml.dump(config, f, default_flow_style=False)

    def create_mock_bigquery_data(self):
        """Create mock BigQuery table metadata."""
        return {
            "test_dataset.users": {
                "table_id": "users",
                "dataset_id": "test_dataset",
                "project_id": "test-project",
                "table_description": "User information table",
                "columns": [
                    {
                        "name": "user_pk",
                        "type": "INTEGER",
                        "standardized_type": "INTEGER",
                        "description": "Primary key for users",
                        "is_primary_key": True,
                    },
                    {
                        "name": "email",
                        "type": "STRING",
                        "standardized_type": "STRING",
                        "description": "User email address",
                    },
                    {
                        "name": "created_at",
                        "type": "TIMESTAMP",
                        "standardized_type": "TIMESTAMP",
                        "description": "Account creation timestamp",
                    },
                ],
            },
            "test_dataset.orders": {
                "table_id": "orders",
                "dataset_id": "test_dataset",
                "project_id": "test-project",
                "table_description": "Order information",
                "columns": [
                    {
                        "name": "order_pk",
                        "type": "INTEGER",
                        "standardized_type": "INTEGER",
                        "description": "Primary key for orders",
                    },
                    {
                        "name": "user_fk",
                        "type": "INTEGER",
                        "standardized_type": "INTEGER",
                        "description": "Foreign key to users",
                    },
                    {
                        "name": "order_amount",
                        "type": "NUMERIC",
                        "standardized_type": "NUMERIC",
                        "description": "Order amount",
                    },
                ],
            },
        }

    @patch("actions.looker.generate.BigQueryClient")
    @patch("actions.looker.generate.get_bigquery_credentials")
    @patch("actions.looker.generate.get_bigquery_location")
    def test_generate_command_successful_execution(self, mock_location, mock_creds, mock_bq_client):
        """Test successful generate command execution."""
        # Mock BigQuery setup
        mock_creds.return_value = (Mock(), "test-project")
        mock_location.return_value = "US"

        # Mock BigQuery client
        mock_client_instance = Mock()
        mock_client_instance.test_connection.return_value = True
        mock_client_instance.get_tables_metadata.return_value = self.create_mock_bigquery_data()
        mock_client_instance.get_error_tracker.return_value = Mock(print_summary=Mock())
        mock_bq_client.return_value = mock_client_instance

        # Create looker project directory
        Path("looker_project/views").mkdir(parents=True)

        result = self.runner.invoke(cli, ["looker", "generate"])

        assert result.exit_code == 0
        assert "Starting LookML generation" in result.output
        assert "Successfully generated LookML project" in result.output

    @patch("actions.looker.generate.BigQueryClient")
    @patch("actions.looker.generate.get_bigquery_credentials")
    @patch("actions.looker.generate.get_bigquery_location")
    def test_generate_command_creates_output_files(self, mock_location, mock_creds, mock_bq_client):
        """Test that generate command creates the expected output files."""
        # Mock BigQuery setup
        mock_creds.return_value = (Mock(), "test-project")
        mock_location.return_value = "US"

        mock_client_instance = Mock()
        mock_client_instance.test_connection.return_value = True
        mock_client_instance.get_tables_metadata.return_value = self.create_mock_bigquery_data()
        mock_client_instance.get_error_tracker.return_value = Mock(print_summary=Mock())
        mock_bq_client.return_value = mock_client_instance

        # Create looker project directory
        Path("looker_project/views").mkdir(parents=True)

        result = self.runner.invoke(cli, ["looker", "generate"])

        assert result.exit_code == 0

        # Check that output files were created
        views_file = Path("looker_project/views/generated_views.view.lkml")

        assert views_file.exists()

        # Check file contents contain expected LookML
        views_content = views_file.read_text()
        assert "view: users {" in views_content
        assert "view: orders {" in views_content
        assert "sql_table_name:" in views_content

    def test_generate_command_missing_config_file(self):
        """Test generate command when concordia.yaml is missing."""
        os.remove("concordia.yaml")

        result = self.runner.invoke(cli, ["looker", "generate"])

        assert result.exit_code != 0
        assert "Configuration error" in result.output

    @patch("actions.looker.generate.BigQueryClient")
    @patch("actions.looker.generate.get_bigquery_credentials")
    @patch("actions.looker.generate.get_bigquery_location")
    def test_generate_command_bigquery_connection_failure(self, mock_location, mock_creds, mock_bq_client):
        """Test generate command when BigQuery connection fails."""
        mock_creds.return_value = (Mock(), "test-project")
        mock_location.return_value = "US"

        # Mock connection failure
        mock_client_instance = Mock()
        mock_client_instance.test_connection.return_value = False
        mock_bq_client.return_value = mock_client_instance

        result = self.runner.invoke(cli, ["looker", "generate"])

        assert result.exit_code == 0
        assert "BigQuery connection test failed" in result.output

    @patch("actions.looker.generate.BigQueryClient")
    @patch("actions.looker.generate.get_bigquery_credentials")
    @patch("actions.looker.generate.get_bigquery_location")
    def test_generate_command_no_tables_found(self, mock_location, mock_creds, mock_bq_client):
        """Test generate command when no tables are found."""
        mock_creds.return_value = (Mock(), "test-project")
        mock_location.return_value = "US"

        mock_client_instance = Mock()
        mock_client_instance.test_connection.return_value = True
        mock_client_instance.get_tables_metadata.return_value = {}  # No tables
        mock_client_instance.get_error_tracker.return_value = Mock(print_summary=Mock())
        mock_bq_client.return_value = mock_client_instance

        result = self.runner.invoke(cli, ["looker", "generate"])

        assert result.exit_code == 0
        assert "No tables found" in result.output

    @patch("actions.looker.generate.BigQueryClient")
    @patch("actions.looker.generate.get_bigquery_credentials")
    @patch("actions.looker.generate.get_bigquery_location")
    def test_generate_command_file_write_error(self, mock_location, mock_creds, mock_bq_client):
        """Test generate command when file writing fails."""
        mock_creds.return_value = (Mock(), "test-project")
        mock_location.return_value = "US"

        mock_client_instance = Mock()
        mock_client_instance.test_connection.return_value = True
        mock_client_instance.get_tables_metadata.return_value = self.create_mock_bigquery_data()
        mock_client_instance.get_error_tracker.return_value = Mock(print_summary=Mock())
        mock_bq_client.return_value = mock_client_instance

        # Create read-only directory to cause write error
        looker_dir = Path("looker_project/views")
        looker_dir.mkdir(parents=True)

        if os.name != "nt":  # Skip permission test on Windows
            os.chmod(looker_dir, 0o444)

            result = self.runner.invoke(cli, ["looker", "generate"])

            # Should handle error gracefully by catching it and reporting failure
            assert result.exit_code != 0
            assert "❌ Unexpected error" in result.output

            # Restore permissions for cleanup
            os.chmod(looker_dir, 0o755)  # noqa: S103 this is a cleanup action for a test
        else:
            # On Windows, just verify the command runs without the permission restriction
            result = self.runner.invoke(cli, ["looker", "generate"])
            # Windows doesn't enforce the same permission model, so command may succeed
            # Just ensure it doesn't crash
            # Either success or controlled failure
            assert result.exit_code in [0, 1]

    @patch("actions.looker.generate.BigQueryClient")
    @patch("actions.looker.generate.get_bigquery_credentials")
    @patch("actions.looker.generate.get_bigquery_location")
    def test_generate_command_with_error_details(self, mock_location, mock_creds, mock_bq_client):
        """Test generate command error handling with detailed error reporting."""
        mock_creds.return_value = (Mock(), "test-project")
        mock_location.return_value = "US"

        # Mock unexpected error
        mock_bq_client.side_effect = Exception("Unexpected BigQuery error")

        # Mock user input to show error details
        with patch("click.confirm", return_value=True):
            result = self.runner.invoke(cli, ["looker", "generate"])

        assert result.exit_code != 0
        assert "Unexpected error" in result.output

    def test_generate_command_invalid_yaml_config(self):
        """Test generate command with invalid YAML configuration."""
        # Create invalid YAML
        with open("concordia.yaml", "w") as f:
            f.write("invalid: yaml: content: [unclosed")

        result = self.runner.invoke(cli, ["looker", "generate"])

        assert result.exit_code != 0
        assert "Configuration error" in result.output

    @patch("actions.looker.generate.BigQueryClient")
    @patch("actions.looker.generate.get_bigquery_credentials")
    @patch("actions.looker.generate.get_bigquery_location")
    def test_generate_command_partial_data_success(self, mock_location, mock_creds, mock_bq_client):
        """Test generate command with partial table data."""
        mock_creds.return_value = (Mock(), "test-project")
        mock_location.return_value = "US"

        # Mock partial table data (missing some expected fields)
        partial_data = {
            "test_dataset.users": {
                "table_id": "users",
                "dataset_id": "test_dataset",
                "project_id": "test-project",
                "columns": [
                    {
                        "name": "id",
                        "type": "INTEGER",
                        "standardized_type": "INTEGER",
                        # Missing description
                    }
                ],
                # Missing table_description
            }
        }

        mock_client_instance = Mock()
        mock_client_instance.test_connection.return_value = True
        mock_client_instance.get_tables_metadata.return_value = partial_data
        mock_client_instance.get_error_tracker.return_value = Mock(print_summary=Mock())
        mock_bq_client.return_value = mock_client_instance

        Path("looker_project/views").mkdir(parents=True)

        result = self.runner.invoke(cli, ["looker", "generate"])

        assert result.exit_code == 0
        assert "Successfully generated LookML project" in result.output


class TestGenerateFunctionUnit:
    """Unit tests for the generate_lookml function."""

    def setup_method(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)

    def teardown_method(self):
        """Clean up test environment."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)

    @patch("actions.looker.generate.load_config")
    def test_generate_lookml_config_loading_error(self, mock_load_config):
        """Test generate_lookml when config loading fails."""
        from actions.looker.config_loader import ConfigurationError

        mock_load_config.side_effect = ConfigurationError("Config not found")

        # Capture output using click testing
        from click.testing import CliRunner

        CliRunner()

        with patch("actions.looker.generate.click.echo") as mock_echo:
            with pytest.raises(click.ClickException) as exc_info:
                generate_lookml()

            # Check that configuration error was handled
            mock_echo.assert_called()
            args = [call.args[0] for call in mock_echo.call_args_list]
            assert any("Configuration error" in arg for arg in args)
            assert "Configuration error" in str(exc_info.value)

    @patch("actions.looker.generate.load_config")
    @patch("actions.looker.generate.get_bigquery_credentials")
    def test_generate_lookml_credentials_error(self, mock_creds, mock_load_config):
        """Test generate_lookml when credentials loading fails."""
        from actions.models.config import (
            ConcordiaConfig,
            ConnectionConfig,
            LookerConfig,
            ModelRules,
        )

        mock_config = ConcordiaConfig(
            connection=ConnectionConfig(datasets=["test"]),
            looker=LookerConfig(
                project_path="./test/",
                views_path="views/test.view.lkml",
                connection="test-connection",
            ),
            model_rules=ModelRules(type_mapping=[]),
        )
        mock_load_config.return_value = mock_config
        mock_creds.side_effect = Exception("Credentials error")

        with (
            patch("actions.looker.generate.click.echo") as mock_echo,
            patch("actions.looker.generate.click.confirm", return_value=False),
        ):
            with pytest.raises(click.ClickException) as exc_info:
                generate_lookml()

            args = [call.args[0] for call in mock_echo.call_args_list]
            assert any("Unexpected error" in arg for arg in args)
            assert "Unexpected error" in str(exc_info.value)

    @patch("actions.looker.generate.load_config")
    @patch("actions.looker.generate.get_bigquery_credentials")
    @patch("actions.looker.generate.get_bigquery_location")
    @patch("actions.looker.generate.BigQueryClient")
    def test_generate_lookml_complete_workflow(self, mock_bq_client, mock_location, mock_creds, mock_load_config):
        """Test complete generate_lookml workflow."""
        # Import required models
        from actions.models.config import (
            ConcordiaConfig,
            ConnectionConfig,
            DefaultBehaviors,
            LookerConfig,
            ModelRules,
            NamingConventions,
        )

        # Create a proper ConcordiaConfig object
        mock_config = ConcordiaConfig(
            connection=ConnectionConfig(datasets=["test_dataset"]),
            looker=LookerConfig(
                project_path="./test_looker/",
                views_path="views/test.view.lkml",
                connection="test-connection",
            ),
            model_rules=ModelRules(
                naming_conventions=NamingConventions(pk_suffix="_pk"),
                defaults=DefaultBehaviors(measures=["count"]),
                type_mapping=[],
            ),
        )

        mock_load_config.return_value = mock_config
        mock_creds.return_value = (Mock(), "test-project")
        mock_location.return_value = "US"

        mock_client_instance = Mock()
        mock_client_instance.test_connection.return_value = True
        mock_client_instance.get_tables_metadata.return_value = {
            "test_dataset.sample": {
                "table_id": "sample",
                "dataset_id": "test_dataset",
                "project_id": "test-project",
                "columns": [],
            }
        }
        mock_client_instance.get_error_tracker.return_value = Mock(print_summary=Mock())
        mock_bq_client.return_value = mock_client_instance

        # Create output directory
        Path("test_looker/views").mkdir(parents=True)

        # Mock the generators and file writer
        with patch("actions.looker.generate.LookMLGenerator") as mock_generator:
            with patch("actions.looker.generate.LookMLFileWriter") as mock_writer:
                mock_gen_instance = Mock()
                # Create a proper LookMLProject object with some content
                from actions.models.lookml import LookMLProject, LookMLView

                mock_project = LookMLProject()
                # Add a mock view to make project_dict non-empty
                mock_view = LookMLView(
                    name="sample",
                    sql_table_name="test.sample",
                    connection="test-connection",
                )
                mock_project.add_view(mock_view)
                mock_gen_instance.generate_complete_lookml_project.return_value = mock_project
                mock_generator.return_value = mock_gen_instance

                mock_writer_instance = Mock()
                mock_writer_instance.write_complete_project.return_value = [
                    "test_looker/views/test.view.lkml",
                    "test_looker/views/explores.view.lkml",
                ]
                mock_writer.return_value = mock_writer_instance

                with patch("actions.looker.generate.click.echo") as mock_echo:
                    generate_lookml()

                # Verify the workflow was executed
                mock_client_instance.test_connection.assert_called_once()
                mock_client_instance.get_tables_metadata.assert_called_once()
                mock_gen_instance.generate_complete_lookml_project.assert_called_once()
                mock_writer_instance.write_complete_project.assert_called_once()

                # Check success message was printed
                args = [call.args[0] for call in mock_echo.call_args_list]
                assert any("Successfully generated LookML project" in arg for arg in args)
