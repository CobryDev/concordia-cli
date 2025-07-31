"""
Unit tests for the config_loader module.
"""

import pytest
import tempfile
import os
import yaml
from unittest.mock import patch, Mock
from actions.looker.config_loader import (
    load_config,
    get_bigquery_credentials,
    get_bigquery_location,
    ConfigurationError,
    _validate_config
)


class TestConfigLoader:
    """Test configuration loading functionality."""

    def test_load_config_file_not_found(self):
        """Test load_config raises error when file doesn't exist."""
        with pytest.raises(ConfigurationError) as exc_info:
            load_config("non_existent_file.yaml")

        assert "not found" in str(exc_info.value)
        assert "concordia init" in str(exc_info.value)

    def test_load_config_invalid_yaml(self):
        """Test load_config raises error for invalid YAML."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [unclosed")
            temp_path = f.name

        try:
            with pytest.raises(ConfigurationError) as exc_info:
                load_config(temp_path)

            assert "Invalid YAML" in str(exc_info.value)
        finally:
            os.unlink(temp_path)

    def test_load_config_success(self):
        """Test load_config successfully loads valid configuration."""
        config_data = {
            'connection': {
                'project_id': 'test-project',
                'datasets': ['test_dataset']
            },
            'looker': {
                'project_path': './looker',
                'views_path': 'views/generated.view.lkml',
                'explores_path': 'explores/generated.explore.lkml',
                'connection': 'test_connection'
            },
            'model_rules': {}
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            config = load_config(temp_path)
            assert config == config_data
        finally:
            os.unlink(temp_path)

    def test_validate_config_missing_sections(self):
        """Test _validate_config raises error for missing required sections."""
        config = {'connection': {}}  # Missing 'looker' and 'model_rules'

        with pytest.raises(ConfigurationError) as exc_info:
            _validate_config(config)

        assert "Missing required section" in str(exc_info.value)

    def test_validate_config_missing_datasets(self):
        """Test _validate_config raises error for missing datasets."""
        config = {
            'connection': {},  # Missing datasets
            'looker': {
                'project_path': './looker',
                'views_path': 'views/generated.view.lkml',
                'explores_path': 'explores/generated.explore.lkml',
                'connection': 'test_connection'
            },
            'model_rules': {}
        }

        with pytest.raises(ConfigurationError) as exc_info:
            _validate_config(config)

        assert "At least one dataset must be specified" in str(exc_info.value)

    def test_validate_config_missing_looker_fields(self):
        """Test _validate_config raises error for missing looker fields."""
        config = {
            'connection': {'datasets': ['test_dataset']},
            'looker': {'project_path': './looker'},  # Missing required fields
            'model_rules': {}
        }

        with pytest.raises(ConfigurationError) as exc_info:
            _validate_config(config)

        assert "Missing required field" in str(exc_info.value)

    @patch('actions.looker.config_loader.default')
    def test_get_bigquery_credentials_application_default(self, mock_default):
        """Test get_bigquery_credentials using application default credentials."""
        # Mock successful default credentials
        mock_credentials = Mock()
        mock_default.return_value = (mock_credentials, 'default-project')

        config = {
            'connection': {
                'project_id': 'test-project'
            }
        }

        credentials, project_id = get_bigquery_credentials(config)

        assert credentials == mock_credentials
        assert project_id == 'test-project'

    @patch('actions.looker.config_loader.default')
    def test_get_bigquery_credentials_no_project_id(self, mock_default):
        """Test get_bigquery_credentials raises error when no valid project_id."""
        mock_credentials = Mock()
        mock_default.return_value = (mock_credentials, None)

        config = {
            'connection': {}
        }

        with pytest.raises(ConfigurationError) as exc_info:
            get_bigquery_credentials(config)

        assert "No valid project_id found" in str(exc_info.value)

    def test_get_bigquery_location_default(self):
        """Test get_bigquery_location returns None when no location configured."""
        config = {'connection': {}}

        location = get_bigquery_location(config)

        assert location is None

    def test_get_bigquery_location_from_config(self):
        """Test get_bigquery_location returns configured location."""
        config = {
            'connection': {
                'location': 'EU'
            }
        }

        location = get_bigquery_location(config)

        assert location == 'EU'
