"""
Unit tests for the config_loader module.
"""

import json
import os
import tempfile
from unittest.mock import Mock, patch

import pytest
import yaml

from actions.looker.config_loader import (
    ConfigurationError,
    _load_dataform_credentials,
    _parse_dataform_config,
    get_bigquery_credentials,
    get_bigquery_location,
    load_config,
)
from actions.models.config import (
    ConcordiaConfig,
    ConnectionConfig,
    DefaultBehaviors,
    LookerConfig,
    LookMLParams,
    ModelRules,
    NamingConventions,
    TypeMapping,
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
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
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
            "connection": {"project_id": "test-project", "datasets": ["test_dataset"]},
            "looker": {
                "project_path": "./looker",
                "views_path": "views/generated.view.lkml",
                "connection": "test_connection",
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
                    }
                ],
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            config = load_config(temp_path)
            # Compare key attributes instead of direct equality since it's now a Pydantic model
            assert config.connection.datasets == config_data["connection"]["datasets"]
            assert config.looker.project_path == config_data["looker"]["project_path"]
            assert config.looker.views_path == config_data["looker"]["views_path"]
            assert config.looker.connection == config_data["looker"]["connection"]
        finally:
            os.unlink(temp_path)

    def test_load_config_validation_missing_sections(self):
        """Test load_config raises error for missing required sections
        through Pydantic validation."""
        # Create a temporary file with invalid config
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({"connection": {"datasets": ["test"]}}, f)
            temp_file = f.name

        try:
            with pytest.raises(ConfigurationError) as exc_info:
                load_config(temp_file)

            assert "looker" in str(exc_info.value) or "field required" in str(exc_info.value)
        finally:
            os.unlink(temp_file)

    def test_load_config_validation_missing_datasets(self):
        """Test load_config raises error for missing datasets through Pydantic validation."""
        # Create a temporary file with invalid config
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(
                {
                    "connection": {},
                    "looker": {
                        "project_path": "test",
                        "views_path": "test",
                        "connection": "test",
                    },
                    "model_rules": {
                        "naming_conventions": {"pk_suffix": "_pk", "fk_suffix": "_fk"},
                        "defaults": {
                            "measures": ["count"],
                            "hide_fields_by_suffix": ["_pk"],
                        },
                        "type_mapping": [],
                    },
                },
                f,
            )
            temp_file = f.name

        try:
            with pytest.raises(ConfigurationError) as exc_info:
                load_config(temp_file)

            assert "datasets" in str(exc_info.value) or "field required" in str(exc_info.value)
        finally:
            os.unlink(temp_file)

    def test_load_config_validation_missing_looker_fields(self):
        """Test load_config raises error for missing looker fields through Pydantic validation."""
        # Create a temporary file with invalid config
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(
                {
                    "connection": {"datasets": ["test"]},
                    "looker": {"project_path": "test"},
                    "model_rules": {
                        "naming_conventions": {"pk_suffix": "_pk", "fk_suffix": "_fk"},
                        "defaults": {
                            "measures": ["count"],
                            "hide_fields_by_suffix": ["_pk"],
                        },
                        "type_mapping": [],
                    },
                },
                f,
            )
            temp_file = f.name

        try:
            with pytest.raises(ConfigurationError) as exc_info:
                load_config(temp_file)

            assert "views_path" in str(exc_info.value) or "connection" in str(exc_info.value)
        finally:
            os.unlink(temp_file)

    @patch("actions.looker.config_loader.default")
    def test_get_bigquery_credentials_application_default(self, mock_default):
        """Test get_bigquery_credentials using application default credentials."""
        # Mock successful default credentials
        mock_credentials = Mock()
        mock_default.return_value = (mock_credentials, "default-project")

        config = ConcordiaConfig(
            connection=ConnectionConfig(project_id="test-project", datasets=["test"]),
            looker=LookerConfig(project_path="./test", views_path="test.lkml", connection="test"),
            model_rules=ModelRules(
                naming_conventions=NamingConventions(pk_suffix="_pk", fk_suffix="_fk"),
                defaults=DefaultBehaviors(measures=["count"], hide_fields_by_suffix=["_pk"]),
                type_mapping=[
                    TypeMapping(
                        bq_type="STRING",
                        lookml_type="dimension",
                        lookml_params=LookMLParams(type="string"),
                    )
                ],
            ),
        )

        credentials, project_id = get_bigquery_credentials(config)

        assert credentials == mock_credentials
        assert project_id == "test-project"

    @patch("actions.looker.config_loader.default")
    def test_get_bigquery_credentials_no_project_id(self, mock_default):
        """Test get_bigquery_credentials raises error when no valid project_id."""
        mock_credentials = Mock()
        mock_default.return_value = (mock_credentials, None)

        config = ConcordiaConfig(
            connection=ConnectionConfig(project_id=None, datasets=["test"]),
            looker=LookerConfig(project_path="./test", views_path="test.lkml", connection="test"),
            model_rules=ModelRules(
                naming_conventions=NamingConventions(pk_suffix="_pk", fk_suffix="_fk"),
                defaults=DefaultBehaviors(measures=["count"], hide_fields_by_suffix=["_pk"]),
                type_mapping=[
                    TypeMapping(
                        bq_type="STRING",
                        lookml_type="dimension",
                        lookml_params=LookMLParams(type="string"),
                    )
                ],
            ),
        )

        with pytest.raises(ConfigurationError) as exc_info:
            get_bigquery_credentials(config)

        assert "No valid project_id found" in str(exc_info.value)

    def test_get_bigquery_location_default(self):
        """Test get_bigquery_location returns None when no location configured."""
        config = ConcordiaConfig(
            connection=ConnectionConfig(datasets=["test"]),
            looker=LookerConfig(project_path="./test", views_path="test.lkml", connection="test"),
            model_rules=ModelRules(
                naming_conventions=NamingConventions(pk_suffix="_pk", fk_suffix="_fk"),
                defaults=DefaultBehaviors(measures=["count"], hide_fields_by_suffix=["_pk"]),
                type_mapping=[
                    TypeMapping(
                        bq_type="STRING",
                        lookml_type="dimension",
                        lookml_params=LookMLParams(type="string"),
                    )
                ],
            ),
        )

        location = get_bigquery_location(config)

        assert location is None

    def test_get_bigquery_location_from_config(self):
        """Test get_bigquery_location returns configured location."""
        config = ConcordiaConfig(
            connection=ConnectionConfig(location="EU", datasets=["test"]),
            looker=LookerConfig(project_path="./test", views_path="test.lkml", connection="test"),
            model_rules=ModelRules(
                naming_conventions=NamingConventions(pk_suffix="_pk", fk_suffix="_fk"),
                defaults=DefaultBehaviors(measures=["count"], hide_fields_by_suffix=["_pk"]),
                type_mapping=[
                    TypeMapping(
                        bq_type="STRING",
                        lookml_type="dimension",
                        lookml_params=LookMLParams(type="string"),
                    )
                ],
            ),
        )

        location = get_bigquery_location(config)

        assert location == "EU"

    def test_get_bigquery_location_from_credentials_file(self):
        """Test get_bigquery_location extracts location from credentials file."""
        # Create a temporary credentials file with location
        creds_data = {"projectId": "test-project", "location": "US"}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(creds_data, f)
            creds_path = f.name

        try:
            config = ConcordiaConfig(
                connection=ConnectionConfig(dataform_credentials_file=creds_path, datasets=["test"]),
                looker=LookerConfig(project_path="./test", views_path="test.lkml", connection="test"),
                model_rules=ModelRules(
                    naming_conventions=NamingConventions(pk_suffix="_pk", fk_suffix="_fk"),
                    defaults=DefaultBehaviors(measures=["count"], hide_fields_by_suffix=["_pk"]),
                    type_mapping=[
                        TypeMapping(
                            bq_type="STRING",
                            lookml_type="dimension",
                            lookml_params=LookMLParams(type="string"),
                        )
                    ],
                ),
            )

            location = get_bigquery_location(config)
            assert location == "US"
        finally:
            os.unlink(creds_path)

    def test_parse_dataform_config_success(self):
        """Test _parse_dataform_config successfully parses valid JSON."""
        creds_data = {"projectId": "test-project", "location": "US"}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(creds_data, f)
            creds_path = f.name

        try:
            result = _parse_dataform_config(creds_path)
            assert result == creds_data
        finally:
            os.unlink(creds_path)

    @patch("actions.looker.config_loader.service_account")
    def test_load_dataform_credentials_service_account_format(self, mock_service_account):
        """Test _load_dataform_credentials with service account format."""
        # Mock service account credentials
        mock_credentials = Mock()
        mock_service_account.Credentials.from_service_account_info.return_value = mock_credentials

        # Service account format with nested credentials
        creds_data = {
            "credentials": {
                "type": "service_account",
                "project_id": "test-project-sa",
                "private_key_id": "key_id",
                "private_key": "-----BEGIN PRIVATE KEY-----\nfake_key\n-----END PRIVATE KEY-----\n",
                "client_email": "test@test-project-sa.iam.gserviceaccount.com",
                "client_id": "12345",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(creds_data, f)
            creds_path = f.name

        try:
            credentials, project_id = _load_dataform_credentials(creds_path)

            assert credentials == mock_credentials
            assert project_id == "test-project-sa"
            mock_service_account.Credentials.from_service_account_info.assert_called_once_with(
                creds_data["credentials"]
            )
        finally:
            os.unlink(creds_path)

    @patch("actions.looker.config_loader.default")
    def test_load_dataform_credentials_simple_format(self, mock_default):
        """Test _load_dataform_credentials with simple format."""
        # Mock application default credentials
        mock_credentials = Mock()
        mock_default.return_value = (mock_credentials, "default-project")

        # Simple format with projectId at root level
        creds_data = {"projectId": "test-project-simple", "location": "US"}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(creds_data, f)
            creds_path = f.name

        try:
            credentials, project_id = _load_dataform_credentials(creds_path)

            assert credentials == mock_credentials
            assert project_id == "test-project-simple"
            mock_default.assert_called_once()
        finally:
            os.unlink(creds_path)

    @patch("actions.looker.config_loader.service_account")
    def test_load_dataform_credentials_service_account_missing_project_id(self, mock_service_account):
        """Test _load_dataform_credentials raises error when service account missing project_id."""
        # Mock service account credentials creation to avoid key validation
        mock_credentials = Mock()
        mock_service_account.Credentials.from_service_account_info.return_value = mock_credentials

        # Service account format missing project_id
        creds_data = {
            "credentials": {
                "type": "service_account",
                "private_key_id": "key_id",
                "private_key": "-----BEGIN PRIVATE KEY-----\nfake_key\n-----END PRIVATE KEY-----\n",
                "client_email": "test@test-project.iam.gserviceaccount.com",
                "client_id": "12345",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                # Missing project_id
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(creds_data, f)
            creds_path = f.name

        try:
            with pytest.raises(ConfigurationError) as exc_info:
                _load_dataform_credentials(creds_path)

            assert "No 'project_id' found in Dataform credentials" in str(exc_info.value)
        finally:
            os.unlink(creds_path)

    def test_load_dataform_credentials_invalid_format(self):
        """Test _load_dataform_credentials raises error for invalid format."""
        # Invalid format - no credentials or projectId
        creds_data = {"some_other_field": "value"}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(creds_data, f)
            creds_path = f.name

        try:
            with pytest.raises(ConfigurationError) as exc_info:
                _load_dataform_credentials(creds_path)

            assert "Invalid credentials file format" in str(exc_info.value)
            assert "Expected either 'credentials' section" in str(exc_info.value)
        finally:
            os.unlink(creds_path)

    @patch("actions.looker.config_loader.default")
    def test_load_dataform_credentials_simple_format_adc_failure(self, mock_default):
        """Test _load_dataform_credentials handles ADC failure for simple format."""
        # Mock ADC failure
        mock_default.side_effect = Exception("ADC not configured")

        # Simple format
        creds_data = {"projectId": "test-project", "location": "US"}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(creds_data, f)
            creds_path = f.name

        try:
            with pytest.raises(ConfigurationError) as exc_info:
                _load_dataform_credentials(creds_path)

            assert "Failed to load Application Default Credentials" in str(exc_info.value)
            assert "gcloud auth application-default login" in str(exc_info.value)
        finally:
            os.unlink(creds_path)

    @patch("actions.looker.config_loader._load_dataform_credentials")
    def test_get_bigquery_credentials_with_dataform_file(self, mock_load_dataform):
        """Test get_bigquery_credentials successfully loads from dataform file."""
        # Mock successful dataform credentials loading
        mock_credentials = Mock()
        mock_load_dataform.return_value = (mock_credentials, "dataform-project")

        # Create a temporary credentials file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"projectId": "test"}, f)
            creds_path = f.name

        try:
            config = ConcordiaConfig(
                connection=ConnectionConfig(
                    dataform_credentials_file=creds_path,
                    project_id="config-project",
                    datasets=["test"],
                ),
                looker=LookerConfig(project_path="./test", views_path="test.lkml", connection="test"),
                model_rules=ModelRules(
                    naming_conventions=NamingConventions(pk_suffix="_pk", fk_suffix="_fk"),
                    defaults=DefaultBehaviors(measures=["count"], hide_fields_by_suffix=["_pk"]),
                    type_mapping=[
                        TypeMapping(
                            bq_type="STRING",
                            lookml_type="dimension",
                            lookml_params=LookMLParams(type="string"),
                        )
                    ],
                ),
            )

            credentials, project_id = get_bigquery_credentials(config)

            # Should use project_id from config, not from dataform file
            assert credentials == mock_credentials
            assert project_id == "config-project"
            mock_load_dataform.assert_called_once_with(creds_path)
        finally:
            os.unlink(creds_path)
