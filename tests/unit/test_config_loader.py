"""
Unit tests for the config_loader module.
"""

import pytest
import tempfile
import os
import yaml
import json
from unittest.mock import patch, Mock
from actions.looker.config_loader import (
    load_config,
    get_bigquery_credentials,
    get_bigquery_location,
    ConfigurationError,
    _validate_config,
    _load_dataform_credentials,
    _parse_dataform_config
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

    def test_get_bigquery_location_from_credentials_file(self):
        """Test get_bigquery_location extracts location from credentials file."""
        # Create a temporary credentials file with location
        creds_data = {
            'projectId': 'test-project',
            'location': 'US'
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(creds_data, f)
            creds_path = f.name

        try:
            config = {
                'connection': {
                    'dataform_credentials_file': creds_path
                    # No location in config - should come from credentials file
                }
            }

            location = get_bigquery_location(config)
            assert location == 'US'
        finally:
            os.unlink(creds_path)

    def test_parse_dataform_config_success(self):
        """Test _parse_dataform_config successfully parses valid JSON."""
        creds_data = {
            'projectId': 'test-project',
            'location': 'US'
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(creds_data, f)
            creds_path = f.name

        try:
            result = _parse_dataform_config(creds_path)
            assert result == creds_data
        finally:
            os.unlink(creds_path)

    @patch('actions.looker.config_loader.service_account')
    def test_load_dataform_credentials_service_account_format(self, mock_service_account):
        """Test _load_dataform_credentials with service account format."""
        # Mock service account credentials
        mock_credentials = Mock()
        mock_service_account.Credentials.from_service_account_info.return_value = mock_credentials

        # Service account format with nested credentials
        creds_data = {
            'credentials': {
                'type': 'service_account',
                'project_id': 'test-project-sa',
                'private_key_id': 'key_id',
                'private_key': '-----BEGIN PRIVATE KEY-----\nfake_key\n-----END PRIVATE KEY-----\n',
                'client_email': 'test@test-project-sa.iam.gserviceaccount.com',
                'client_id': '12345',
                'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                'token_uri': 'https://oauth2.googleapis.com/token'
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(creds_data, f)
            creds_path = f.name

        try:
            credentials, project_id = _load_dataform_credentials(creds_path)

            assert credentials == mock_credentials
            assert project_id == 'test-project-sa'
            mock_service_account.Credentials.from_service_account_info.assert_called_once_with(
                creds_data['credentials']
            )
        finally:
            os.unlink(creds_path)

    @patch('actions.looker.config_loader.default')
    def test_load_dataform_credentials_simple_format(self, mock_default):
        """Test _load_dataform_credentials with simple format."""
        # Mock application default credentials
        mock_credentials = Mock()
        mock_default.return_value = (mock_credentials, 'default-project')

        # Simple format with projectId at root level
        creds_data = {
            'projectId': 'test-project-simple',
            'location': 'US'
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(creds_data, f)
            creds_path = f.name

        try:
            credentials, project_id = _load_dataform_credentials(creds_path)

            assert credentials == mock_credentials
            assert project_id == 'test-project-simple'
            mock_default.assert_called_once()
        finally:
            os.unlink(creds_path)

    @patch('actions.looker.config_loader.service_account')
    def test_load_dataform_credentials_service_account_missing_project_id(self, mock_service_account):
        """Test _load_dataform_credentials raises error when service account missing project_id."""
        # Mock service account credentials creation to avoid key validation
        mock_credentials = Mock()
        mock_service_account.Credentials.from_service_account_info.return_value = mock_credentials

        # Service account format missing project_id
        creds_data = {
            'credentials': {
                'type': 'service_account',
                'private_key_id': 'key_id',
                'private_key': '-----BEGIN PRIVATE KEY-----\nfake_key\n-----END PRIVATE KEY-----\n',
                'client_email': 'test@test-project.iam.gserviceaccount.com',
                'client_id': '12345',
                'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                'token_uri': 'https://oauth2.googleapis.com/token'
                # Missing project_id
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(creds_data, f)
            creds_path = f.name

        try:
            with pytest.raises(ConfigurationError) as exc_info:
                _load_dataform_credentials(creds_path)

            assert "No 'project_id' found in Dataform credentials" in str(
                exc_info.value)
        finally:
            os.unlink(creds_path)

    def test_load_dataform_credentials_invalid_format(self):
        """Test _load_dataform_credentials raises error for invalid format."""
        # Invalid format - no credentials or projectId
        creds_data = {
            'some_other_field': 'value'
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(creds_data, f)
            creds_path = f.name

        try:
            with pytest.raises(ConfigurationError) as exc_info:
                _load_dataform_credentials(creds_path)

            assert "Invalid credentials file format" in str(exc_info.value)
            assert "Expected either 'credentials' section" in str(
                exc_info.value)
        finally:
            os.unlink(creds_path)

    @patch('actions.looker.config_loader.default')
    def test_load_dataform_credentials_simple_format_adc_failure(self, mock_default):
        """Test _load_dataform_credentials handles ADC failure for simple format."""
        # Mock ADC failure
        mock_default.side_effect = Exception("ADC not configured")

        # Simple format
        creds_data = {
            'projectId': 'test-project',
            'location': 'US'
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(creds_data, f)
            creds_path = f.name

        try:
            with pytest.raises(ConfigurationError) as exc_info:
                _load_dataform_credentials(creds_path)

            assert "Failed to load Application Default Credentials" in str(
                exc_info.value)
            assert "gcloud auth application-default login" in str(
                exc_info.value)
        finally:
            os.unlink(creds_path)

    @patch('actions.looker.config_loader._load_dataform_credentials')
    def test_get_bigquery_credentials_with_dataform_file(self, mock_load_dataform):
        """Test get_bigquery_credentials successfully loads from dataform file."""
        # Mock successful dataform credentials loading
        mock_credentials = Mock()
        mock_load_dataform.return_value = (
            mock_credentials, 'dataform-project')

        # Create a temporary credentials file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({'projectId': 'test'}, f)
            creds_path = f.name

        try:
            config = {
                'connection': {
                    'dataform_credentials_file': creds_path,
                    'project_id': 'config-project'  # Should override dataform project
                }
            }

            credentials, project_id = get_bigquery_credentials(config)

            # Should use project_id from config, not from dataform file
            assert credentials == mock_credentials
            assert project_id == 'config-project'
            mock_load_dataform.assert_called_once_with(creds_path)
        finally:
            os.unlink(creds_path)
