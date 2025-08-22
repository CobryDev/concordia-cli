"""
Unit tests for the config_validator module.
"""

import tempfile
from pathlib import Path

import pytest
import yaml

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
from actions.utils.config_validator import (
    ConfigValidationError,
    _check_missing_paths,
    _check_template_values,
    format_validation_errors,
    generate_json_schema,
    load_config_file,
    validate_config_file,
    validate_config_lenient,
    validate_config_strict,
)


class TestLoadConfigFile:
    """Test configuration file loading."""

    def test_load_config_file_not_found(self):
        """Test load_config_file raises error when file doesn't exist."""
        with pytest.raises(ConfigValidationError) as exc_info:
            load_config_file("non_existent_file.yaml")

        assert "Configuration file not found" in str(exc_info.value)
        assert "non_existent_file.yaml" in str(exc_info.value)

    def test_load_config_file_invalid_yaml(self):
        """Test load_config_file raises error for invalid YAML."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [unclosed")
            temp_path = f.name

        try:
            with pytest.raises(ConfigValidationError) as exc_info:
                load_config_file(temp_path)

            assert "Invalid YAML syntax" in str(exc_info.value)
        finally:
            Path(temp_path).unlink()

    def test_load_config_file_empty_file(self):
        """Test load_config_file raises error for empty file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")
            temp_path = f.name

        try:
            with pytest.raises(ConfigValidationError) as exc_info:
                load_config_file(temp_path)

            assert "Configuration file is empty" in str(exc_info.value)
        finally:
            Path(temp_path).unlink()

    def test_load_config_file_not_dict(self):
        """Test load_config_file raises error when file contains non-dict."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(["not", "a", "dict"], f)
            temp_path = f.name

        try:
            with pytest.raises(ConfigValidationError) as exc_info:
                load_config_file(temp_path)

            assert "Configuration must be a YAML object" in str(exc_info.value)
            assert "list" in str(exc_info.value)
        finally:
            Path(temp_path).unlink()

    def test_load_config_file_success(self):
        """Test load_config_file successfully loads valid YAML."""
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
            result = load_config_file(temp_path)
            assert result == config_data
        finally:
            Path(temp_path).unlink()

    def test_load_config_file_read_error(self):
        """Test load_config_file handles file read errors."""
        import platform

        # Skip this test on Windows as file permissions work differently
        if platform.system() == "Windows":
            pytest.skip("File permission tests not reliable on Windows")

        # Create file then make it unreadable (if possible on this platform)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({"test": "config"}, f)
            temp_path = f.name

        try:
            # Change permissions to make file unreadable
            Path(temp_path).chmod(0o000)

            with pytest.raises(ConfigValidationError) as exc_info:
                load_config_file(temp_path)

            assert "Error reading" in str(exc_info.value)
        except PermissionError:
            # Some platforms don't allow this test, skip it
            pytest.skip("Cannot test file permissions on this platform")
        finally:
            # Restore permissions and clean up
            try:
                Path(temp_path).chmod(0o644)
                Path(temp_path).unlink()
            except (OSError, FileNotFoundError):
                pass


class TestValidateConfigStrict:
    """Test strict configuration validation."""

    @pytest.mark.parametrize(
        "template_project_id,should_fail",
        [
            ("your-gcp-project-id", True),
            ("your-project-id", True),
            ("actual-project-123", False),
            ("my-gcp-project", False),
        ],
    )
    def test_validate_config_strict_project_id_templates(self, template_project_id, should_fail):
        """Test strict validation fails on template project IDs."""
        config_data = {
            "connection": {"project_id": template_project_id, "datasets": ["test_dataset"]},
            "looker": {
                "project_path": "./test_looker",
                "views_path": "test.view.lkml",
                "connection": "test_connection",
            },
            "model_rules": {
                "naming_conventions": {"pk_suffix": "_pk", "fk_suffix": "_fk"},
                "defaults": {"measures": ["count"], "hide_fields_by_suffix": ["_pk"]},
                "type_mapping": [
                    {
                        "bq_type": "STRING",
                        "lookml_type": "dimension",
                        "lookml_params": {"type": "string"},
                    }
                ],
            },
        }

        if should_fail:
            with pytest.raises(ConfigValidationError) as exc_info:
                validate_config_strict(config_data)

            assert "template values that must be replaced" in str(exc_info.value)
            assert "connection.project_id" in str(exc_info.value.errors[0]["location"])
            assert "template project ID" in str(exc_info.value.errors[0]["message"])
        else:
            # Should succeed
            config = validate_config_strict(config_data)
            assert config.connection.project_id == template_project_id

    @pytest.mark.parametrize(
        "template_location,should_fail",
        [
            ("your-region", True),
            ("your-location", True),
            ("US", False),
            ("eu-west1", False),
        ],
    )
    def test_validate_config_strict_location_templates(self, template_location, should_fail):
        """Test strict validation fails on template locations."""
        config_data = {
            "connection": {
                "project_id": "actual-project",
                "location": template_location,
                "datasets": ["test_dataset"],
            },
            "looker": {
                "project_path": "./test_looker",
                "views_path": "test.view.lkml",
                "connection": "test_connection",
            },
            "model_rules": {
                "naming_conventions": {"pk_suffix": "_pk", "fk_suffix": "_fk"},
                "defaults": {"measures": ["count"], "hide_fields_by_suffix": ["_pk"]},
                "type_mapping": [
                    {
                        "bq_type": "STRING",
                        "lookml_type": "dimension",
                        "lookml_params": {"type": "string"},
                    }
                ],
            },
        }

        if should_fail:
            with pytest.raises(ConfigValidationError) as exc_info:
                validate_config_strict(config_data)

            assert "template values that must be replaced" in str(exc_info.value)
            assert "connection.location" in str(exc_info.value.errors[0]["location"])
            assert "template location" in str(exc_info.value.errors[0]["message"])
        else:
            # Should succeed
            config = validate_config_strict(config_data)
            assert config.connection.location == template_location

    @pytest.mark.parametrize(
        "template_connection,should_fail",
        [
            ("your-bigquery-connection", True),
            ("your_connection_name", True),
            ("actual_bigquery_conn", False),
            ("prod-bq-connection", False),
        ],
    )
    def test_validate_config_strict_connection_templates(self, template_connection, should_fail):
        """Test strict validation fails on template connection names."""
        config_data = {
            "connection": {"project_id": "actual-project", "datasets": ["test_dataset"]},
            "looker": {
                "project_path": "./test_looker",
                "views_path": "test.view.lkml",
                "connection": template_connection,
            },
            "model_rules": {
                "naming_conventions": {"pk_suffix": "_pk", "fk_suffix": "_fk"},
                "defaults": {"measures": ["count"], "hide_fields_by_suffix": ["_pk"]},
                "type_mapping": [
                    {
                        "bq_type": "STRING",
                        "lookml_type": "dimension",
                        "lookml_params": {"type": "string"},
                    }
                ],
            },
        }

        if should_fail:
            with pytest.raises(ConfigValidationError) as exc_info:
                validate_config_strict(config_data)

            assert "template values that must be replaced" in str(exc_info.value)
            assert "looker.connection" in str(exc_info.value.errors[0]["location"])
            assert "template connection" in str(exc_info.value.errors[0]["message"])
        else:
            # Should succeed
            config = validate_config_strict(config_data)
            assert config.looker.connection == template_connection

    def test_validate_config_strict_empty_type_mapping(self):
        """Test strict validation fails on empty type mapping."""
        config_data = {
            "connection": {"project_id": "actual-project", "datasets": ["test_dataset"]},
            "looker": {
                "project_path": "./test_looker",
                "views_path": "test.view.lkml",
                "connection": "actual_connection",
            },
            "model_rules": {
                "naming_conventions": {"pk_suffix": "_pk", "fk_suffix": "_fk"},
                "defaults": {"measures": ["count"], "hide_fields_by_suffix": ["_pk"]},
                "type_mapping": [],
            },
        }

        with pytest.raises(ConfigValidationError) as exc_info:
            validate_config_strict(config_data)

        assert "template values that must be replaced" in str(exc_info.value)
        assert "model_rules.type_mapping" in str(exc_info.value.errors[0]["location"])
        assert "At least one type mapping is required" in str(exc_info.value.errors[0]["message"])

    def test_validate_config_strict_multiple_errors(self):
        """Test strict validation collects multiple template value errors."""
        config_data = {
            "connection": {
                "project_id": "your-gcp-project-id",
                "location": "your-region",
                "datasets": ["test_dataset"],
            },
            "looker": {
                "project_path": "./test_looker",
                "views_path": "test.view.lkml",
                "connection": "your-bigquery-connection",
            },
            "model_rules": {
                "naming_conventions": {"pk_suffix": "_pk", "fk_suffix": "_fk"},
                "defaults": {"measures": ["count"], "hide_fields_by_suffix": ["_pk"]},
                "type_mapping": [],
            },
        }

        with pytest.raises(ConfigValidationError) as exc_info:
            validate_config_strict(config_data)

        assert "4 template values that must be replaced" in str(exc_info.value)
        assert len(exc_info.value.errors) == 4

        # Check all expected errors are present
        error_locations = [error["location"] for error in exc_info.value.errors]
        assert "connection.project_id" in error_locations
        assert "connection.location" in error_locations
        assert "looker.connection" in error_locations
        assert "model_rules.type_mapping" in error_locations

    def test_validate_config_strict_pydantic_errors(self):
        """Test strict validation handles Pydantic validation errors."""
        config_data = {
            "connection": {"datasets": []},  # Missing required datasets
            "looker": {
                "project_path": "./test_looker",
                "views_path": "test.view.lkml",
                "connection": "test_connection",
            },
            "model_rules": {
                "naming_conventions": {"pk_suffix": "_pk", "fk_suffix": "_fk"},
                "defaults": {"measures": ["count"], "hide_fields_by_suffix": ["_pk"]},
                "type_mapping": [
                    {
                        "bq_type": "STRING",
                        "lookml_type": "dimension",
                        "lookml_params": {"type": "string"},
                    }
                ],
            },
        }

        with pytest.raises(ConfigValidationError) as exc_info:
            validate_config_strict(config_data)

        assert "Configuration validation failed" in str(exc_info.value)
        assert len(exc_info.value.errors) >= 1

    def test_validate_config_strict_success(self):
        """Test strict validation succeeds with valid configuration."""
        config_data = {
            "connection": {"project_id": "actual-project", "datasets": ["test_dataset"]},
            "looker": {
                "project_path": "./test_looker",
                "views_path": "test.view.lkml",
                "connection": "actual_connection",
            },
            "model_rules": {
                "naming_conventions": {"pk_suffix": "_pk", "fk_suffix": "_fk"},
                "defaults": {"measures": ["count"], "hide_fields_by_suffix": ["_pk"]},
                "type_mapping": [
                    {
                        "bq_type": "STRING",
                        "lookml_type": "dimension",
                        "lookml_params": {"type": "string"},
                    }
                ],
            },
        }

        # Should not raise an exception
        config = validate_config_strict(config_data)
        assert isinstance(config, ConcordiaConfig)
        assert config.connection.project_id == "actual-project"


class TestValidateConfigLenient:
    """Test lenient configuration validation."""

    def test_validate_config_lenient_success_no_warnings(self):
        """Test lenient validation succeeds with minimal warnings for good config."""
        config_data = {
            "connection": {"project_id": "actual-project", "datasets": ["test_dataset"]},
            "looker": {
                "project_path": "./test",  # Use a path that might exist or is commonly used for tests
                "views_path": "test.view.lkml",
                "connection": "actual_connection",
            },
            "model_rules": {
                "naming_conventions": {"pk_suffix": "_pk", "fk_suffix": "_fk"},
                "defaults": {"measures": ["count"], "hide_fields_by_suffix": ["_pk"]},
                "type_mapping": [
                    {
                        "bq_type": "STRING",
                        "lookml_type": "dimension",
                        "lookml_params": {"type": "string"},
                    }
                ],
            },
        }

        is_valid, warnings, errors = validate_config_lenient(config_data)

        assert is_valid is True
        # Allow for some warnings about missing directories (this is expected in test environments)
        assert len(errors) == 0

    def test_validate_config_lenient_template_warnings(self):
        """Test lenient validation generates warnings for template values."""
        config_data = {
            "connection": {
                "project_id": "your-gcp-project-id",
                "location": "your-region",
                "datasets": ["test_dataset"],
            },
            "looker": {
                "project_path": "./looker-project",
                "views_path": "views/concordia_views.view.lkml",
                "connection": "your-bigquery-connection",
            },
            "model_rules": {
                "naming_conventions": {"pk_suffix": "_pk", "fk_suffix": "_fk"},
                "defaults": {"measures": ["count"], "hide_fields_by_suffix": ["_pk"]},
                "type_mapping": [
                    {
                        "bq_type": "STRING",
                        "lookml_type": "dimension",
                        "lookml_params": {"type": "string"},
                    }
                ],
            },
        }

        is_valid, warnings, errors = validate_config_lenient(config_data)

        assert is_valid is True
        assert len(errors) == 0
        assert len(warnings) > 0

        # Check that template value warnings are present
        warning_text = " ".join(warnings)
        assert "template value" in warning_text or "Using template" in warning_text

    def test_validate_config_lenient_structural_errors(self):
        """Test lenient validation identifies structural errors."""
        config_data = {
            "connection": {"datasets": []},  # Invalid: empty datasets
            "looker": {
                "project_path": "./test_looker",
                "views_path": "test.view.lkml",
                "connection": "test_connection",
            },
            "model_rules": {
                "naming_conventions": {"pk_suffix": "_pk", "fk_suffix": "_fk"},
                "defaults": {"measures": ["count"], "hide_fields_by_suffix": ["_pk"]},
                "type_mapping": [
                    {
                        "bq_type": "STRING",
                        "lookml_type": "dimension",
                        "lookml_params": {"type": "string"},
                    }
                ],
            },
        }

        is_valid, warnings, errors = validate_config_lenient(config_data)

        assert is_valid is False
        assert len(errors) > 0

    def test_validate_config_lenient_missing_file_warnings(self):
        """Test lenient validation warns about missing files."""
        # Create a config that references non-existent files
        config_data = {
            "connection": {
                "dataform_credentials_file": "./non-existent-creds.json",
                "project_id": "actual-project",
                "datasets": ["test_dataset"],
            },
            "looker": {
                "project_path": "./non-existent-looker",
                "views_path": "test.view.lkml",
                "connection": "actual_connection",
            },
            "model_rules": {
                "naming_conventions": {"pk_suffix": "_pk", "fk_suffix": "_fk"},
                "defaults": {"measures": ["count"], "hide_fields_by_suffix": ["_pk"]},
                "type_mapping": [
                    {
                        "bq_type": "STRING",
                        "lookml_type": "dimension",
                        "lookml_params": {"type": "string"},
                    }
                ],
            },
        }

        is_valid, warnings, errors = validate_config_lenient(config_data)

        # Should be valid structurally but have warnings about missing files
        assert is_valid is True
        assert len(warnings) > 0

        warning_text = " ".join(warnings)
        assert "not found" in warning_text or "does not exist" in warning_text

    def test_validate_config_lenient_unexpected_error(self):
        """Test lenient validation handles unexpected errors gracefully."""
        # Create invalid config data that will cause an unexpected error
        config_data = "not a dict"

        is_valid, warnings, errors = validate_config_lenient(config_data)

        assert is_valid is False
        assert len(errors) > 0
        assert "Unexpected validation error" in errors[0]


class TestCheckTemplateFunctions:
    """Test helper functions for checking template values and missing paths."""

    def test_check_template_values_credentials_file(self):
        """Test _check_template_values identifies template credentials files."""
        config = ConcordiaConfig(
            connection=ConnectionConfig(
                dataform_credentials_file="path/to/your/dataform-credentials.json",
                datasets=["test"],
            ),
            looker=LookerConfig(project_path="./test", views_path="test.view.lkml", connection="test"),
            model_rules=ModelRules(
                naming_conventions=NamingConventions(),
                defaults=DefaultBehaviors(),
                type_mapping=[
                    TypeMapping(
                        bq_type="STRING",
                        lookml_type="dimension",
                        lookml_params=LookMLParams(type="string"),
                    )
                ],
            ),
        )

        warnings = _check_template_values(config)

        assert len(warnings) > 0
        assert any("template value" in warning for warning in warnings)

    def test_check_template_values_missing_df_credentials(self):
        """Test _check_template_values warns about missing .df-credentials.json."""
        config = ConcordiaConfig(
            connection=ConnectionConfig(dataform_credentials_file=".df-credentials.json", datasets=["test"]),
            looker=LookerConfig(project_path="./test", views_path="test.view.lkml", connection="test"),
            model_rules=ModelRules(
                naming_conventions=NamingConventions(),
                defaults=DefaultBehaviors(),
                type_mapping=[
                    TypeMapping(
                        bq_type="STRING",
                        lookml_type="dimension",
                        lookml_params=LookMLParams(type="string"),
                    )
                ],
            ),
        )

        warnings = _check_template_values(config)

        assert len(warnings) > 0
        assert any(".df-credentials.json" in warning for warning in warnings)

    def test_check_missing_paths_credentials_file(self):
        """Test _check_missing_paths identifies missing credentials files."""
        # Create a config with a credentials file that doesn't exist but is not a template value
        with tempfile.TemporaryDirectory() as temp_dir:
            non_existent_path = f"{temp_dir}/missing-creds.json"

            config = ConcordiaConfig(
                connection=ConnectionConfig(
                    # Use common case that won't cause validation error
                    dataform_credentials_file=".df-credentials.json",
                    datasets=["test"],
                ),
                looker=LookerConfig(project_path="./test", views_path="test.view.lkml", connection="test"),
                model_rules=ModelRules(
                    naming_conventions=NamingConventions(),
                    defaults=DefaultBehaviors(),
                    type_mapping=[
                        TypeMapping(
                            bq_type="STRING",
                            lookml_type="dimension",
                            lookml_params=LookMLParams(type="string"),
                        )
                    ],
                ),
            )

            # Manually set the path after creation to bypass validation
            config.connection.dataform_credentials_file = non_existent_path

            warnings = _check_missing_paths(config)

            assert len(warnings) > 0
            assert any("File not found" in warning for warning in warnings)

    def test_check_missing_paths_looker_directory(self):
        """Test _check_missing_paths identifies missing Looker directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            non_existent_path = f"{temp_dir}/non-existent-looker"

            config = ConcordiaConfig(
                connection=ConnectionConfig(datasets=["test"]),
                looker=LookerConfig(project_path="./test", views_path="test.view.lkml", connection="test"),
                model_rules=ModelRules(
                    naming_conventions=NamingConventions(),
                    defaults=DefaultBehaviors(),
                    type_mapping=[
                        TypeMapping(
                            bq_type="STRING",
                            lookml_type="dimension",
                            lookml_params=LookMLParams(type="string"),
                        )
                    ],
                ),
            )

            # Manually set the path after creation to bypass validation
            config.looker.project_path = non_existent_path

            warnings = _check_missing_paths(config)

            assert len(warnings) > 0
            assert any("Directory not found" in warning for warning in warnings)


class TestValidateConfigFile:
    """Test the high-level validate_config_file function."""

    def test_validate_config_file_not_found(self):
        """Test validate_config_file handles missing files."""
        result = validate_config_file("non-existent.yaml")

        assert result["success"] is False
        assert "Configuration file not found" in result["message"]
        assert len(result["errors"]) > 0

    def test_validate_config_file_strict_success(self):
        """Test validate_config_file with strict validation success."""
        config_data = {
            "connection": {"project_id": "actual-project", "datasets": ["test_dataset"]},
            "looker": {
                "project_path": "./test_looker",
                "views_path": "test.view.lkml",
                "connection": "actual_connection",
            },
            "model_rules": {
                "naming_conventions": {"pk_suffix": "_pk", "fk_suffix": "_fk"},
                "defaults": {"measures": ["count"], "hide_fields_by_suffix": ["_pk"]},
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
            result = validate_config_file(temp_path, strict=True)

            assert result["success"] is True
            assert isinstance(result["config"], ConcordiaConfig)
            assert len(result["errors"]) == 0
            assert len(result["warnings"]) == 0
            assert "valid and ready for use" in result["message"]
        finally:
            Path(temp_path).unlink()

    def test_validate_config_file_strict_failure(self):
        """Test validate_config_file with strict validation failure."""
        config_data = {
            "connection": {"project_id": "your-gcp-project-id", "datasets": ["test_dataset"]},
            "looker": {
                "project_path": "./test_looker",
                "views_path": "test.view.lkml",
                "connection": "actual_connection",
            },
            "model_rules": {
                "naming_conventions": {"pk_suffix": "_pk", "fk_suffix": "_fk"},
                "defaults": {"measures": ["count"], "hide_fields_by_suffix": ["_pk"]},
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
            result = validate_config_file(temp_path, strict=True)

            assert result["success"] is False
            assert result["config"] is None
            assert len(result["errors"]) > 0
            assert "template values" in result["message"]
        finally:
            Path(temp_path).unlink()

    def test_validate_config_file_lenient_with_warnings(self):
        """Test validate_config_file with lenient validation and warnings."""
        config_data = {
            "connection": {"project_id": "your-gcp-project-id", "datasets": ["test_dataset"]},
            "looker": {
                "project_path": "./looker-project",
                "views_path": "views/concordia_views.view.lkml",
                "connection": "your-bigquery-connection",
            },
            "model_rules": {
                "naming_conventions": {"pk_suffix": "_pk", "fk_suffix": "_fk"},
                "defaults": {"measures": ["count"], "hide_fields_by_suffix": ["_pk"]},
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
            result = validate_config_file(temp_path, strict=False)

            assert result["success"] is True
            assert isinstance(result["config"], ConcordiaConfig)
            assert len(result["errors"]) == 0
            assert len(result["warnings"]) > 0
            assert "warnings" in result["message"]
        finally:
            Path(temp_path).unlink()


class TestParameterizedInvalidConfigs:
    """Parameterized tests for various invalid configuration snippets."""

    @pytest.mark.parametrize(
        "invalid_config,expected_error_substring",
        [
            # Missing required sections
            ({"connection": {"datasets": ["test"]}}, "Field required"),
            ({"looker": {"project_path": "test"}}, "Field required"),
            # Invalid dataset values
            (
                {
                    "connection": {"datasets": []},
                    "looker": {"project_path": "test", "views_path": "test.lkml", "connection": "test"},
                    "model_rules": {"type_mapping": []},
                },
                "List should have at least 1 item",
            ),
            # Invalid project ID format
            (
                {
                    "connection": {"project_id": "a", "datasets": ["test"]},
                    "looker": {"project_path": "test", "views_path": "test.lkml", "connection": "test"},
                    "model_rules": {"type_mapping": []},
                },
                "between 6 and 30 characters",
            ),
            # Invalid LookML type
            (
                {
                    "connection": {"datasets": ["test"]},
                    "looker": {"project_path": "test", "views_path": "test.lkml", "connection": "test"},
                    "model_rules": {
                        "type_mapping": [
                            {
                                "bq_type": "STRING",
                                "lookml_type": "invalid_type",
                                "lookml_params": {"type": "string"},
                            }
                        ]
                    },
                },
                "Invalid LookML type",
            ),
            # Missing required fields in type mapping
            (
                {
                    "connection": {"datasets": ["test"]},
                    "looker": {"project_path": "test", "views_path": "test.lkml", "connection": "test"},
                    "model_rules": {"type_mapping": [{"bq_type": "STRING"}]},
                },
                "Field required",
            ),
        ],
    )
    def test_various_invalid_configs_lenient(self, invalid_config, expected_error_substring):
        """Test lenient validation with various invalid configurations."""
        is_valid, warnings, errors = validate_config_lenient(invalid_config)

        if expected_error_substring:
            # Some errors might be warnings in lenient mode
            all_messages = errors + warnings
            assert any(expected_error_substring in msg for msg in all_messages), (
                f"Expected '{expected_error_substring}' in errors/warnings: {all_messages}"
            )

    @pytest.mark.parametrize(
        "invalid_config,expected_error_substring",
        [
            # These should definitely fail strict validation
            (
                {
                    "connection": {"project_id": "your-gcp-project-id", "datasets": ["test"]},
                    "looker": {"project_path": "test", "views_path": "test.lkml", "connection": "test"},
                    "model_rules": {
                        "type_mapping": [
                            {
                                "bq_type": "STRING",
                                "lookml_type": "dimension",
                                "lookml_params": {"type": "string"},
                            }
                        ]
                    },
                },
                "template values",
            ),
            (
                {
                    "connection": {"datasets": ["test"]},
                    "looker": {
                        "project_path": "test",
                        "views_path": "test.lkml",
                        "connection": "your-bigquery-connection",
                    },
                    "model_rules": {
                        "type_mapping": [
                            {
                                "bq_type": "STRING",
                                "lookml_type": "dimension",
                                "lookml_params": {"type": "string"},
                            }
                        ]
                    },
                },
                "template values",
            ),
        ],
    )
    def test_various_invalid_configs_strict(self, invalid_config, expected_error_substring):
        """Test strict validation with various invalid configurations."""
        with pytest.raises(ConfigValidationError) as exc_info:
            validate_config_strict(invalid_config)

        assert expected_error_substring in str(exc_info.value)


class TestUtilityFunctions:
    """Test utility functions."""

    def test_format_validation_errors_empty(self):
        """Test format_validation_errors with empty list."""
        result = format_validation_errors([])
        assert result == "No errors found."

    def test_format_validation_errors_with_errors(self):
        """Test format_validation_errors with actual errors."""
        errors = [
            {"location": "connection.project_id", "message": "Template value detected"},
            {"location": "looker.connection", "message": "Invalid connection name"},
        ]

        result = format_validation_errors(errors)

        assert "connection.project_id: Template value detected" in result
        assert "looker.connection: Invalid connection name" in result
        assert result.count("•") == 2

    def test_generate_json_schema(self):
        """Test generate_json_schema returns valid schema."""
        schema = generate_json_schema()

        assert isinstance(schema, dict)
        assert "properties" in schema
        assert "connection" in schema["properties"]
        assert "looker" in schema["properties"]
        assert "model_rules" in schema["properties"]
