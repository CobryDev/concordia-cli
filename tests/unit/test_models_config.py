"""
Unit tests for Pydantic models in actions/models/config.py.

Tests custom validators, field validation logic, and model-level validation
to ensure configuration models properly validate input data.
"""

import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

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


class TestConnectionConfig:
    """Test ConnectionConfig validators and validation logic."""

    def test_valid_connection_config(self):
        """Test creation with valid configuration."""
        config = ConnectionConfig(
            dataform_credentials_file=".df-credentials.json",
            project_id="test-project-123",
            location="US",
            datasets=["raw_data", "analytics"],
        )

        assert config.dataform_credentials_file == ".df-credentials.json"
        assert config.project_id == "test-project-123"
        assert config.location == "US"
        assert config.datasets == ["raw_data", "analytics"]

    def test_dataform_credentials_file_validator_none(self):
        """Test credentials file validator with None value."""
        config = ConnectionConfig(datasets=["test"])
        assert config.dataform_credentials_file is None

    def test_dataform_credentials_file_validator_template_values(self):
        """Test credentials file validator allows template values."""
        config = ConnectionConfig(
            dataform_credentials_file="path/to/your/dataform-credentials.json",
            datasets=["test"],
        )
        assert config.dataform_credentials_file == "path/to/your/dataform-credentials.json"

    def test_dataform_credentials_file_validator_common_path(self):
        """Test credentials file validator allows common .df-credentials.json path."""
        config = ConnectionConfig(
            dataform_credentials_file=".df-credentials.json",
            datasets=["test"],
        )
        assert config.dataform_credentials_file == ".df-credentials.json"

    def test_dataform_credentials_file_validator_nonexistent_file(self):
        """Test credentials file validator rejects non-existent files."""
        with pytest.raises(ValidationError) as exc_info:
            ConnectionConfig(
                dataform_credentials_file="/nonexistent/path/credentials.json",
                datasets=["test"],
            )
        assert "Dataform credentials file not found" in str(exc_info.value)

    def test_dataform_credentials_file_validator_existing_file(self):
        """Test credentials file validator accepts existing files."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            config = ConnectionConfig(
                dataform_credentials_file=tmp_path,
                datasets=["test"],
            )
            assert config.dataform_credentials_file == tmp_path
        finally:
            Path(tmp_path).unlink()

    def test_dataform_credentials_file_validator_directory_error(self):
        """Test credentials file validator rejects directories."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            with pytest.raises(ValidationError) as exc_info:
                ConnectionConfig(
                    dataform_credentials_file=tmp_dir,
                    datasets=["test"],
                )
            assert "is not a file" in str(exc_info.value)

    def test_dataform_credentials_file_validator_wrong_extension(self):
        """Test credentials file validator rejects non-JSON files."""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            with pytest.raises(ValidationError) as exc_info:
                ConnectionConfig(
                    dataform_credentials_file=tmp_path,
                    datasets=["test"],
                )
            assert "must be a .json file" in str(exc_info.value)
        finally:
            Path(tmp_path).unlink()

    def test_project_id_validator_none(self):
        """Test project ID validator with None value."""
        config = ConnectionConfig(datasets=["test"])
        assert config.project_id is None

    def test_project_id_validator_template_values(self):
        """Test project ID validator allows template values."""
        for template_id in ["your-gcp-project-id", "your-project-id"]:
            config = ConnectionConfig(
                project_id=template_id, datasets=["test"])
            assert config.project_id == template_id

    def test_project_id_validator_valid_ids(self):
        """Test project ID validator accepts valid GCP project IDs."""
        valid_ids = [
            "test-project",
            "test_project",
            "test-123",
            "project123",
            "my-long-project-name-123",
        ]

        for project_id in valid_ids:
            config = ConnectionConfig(project_id=project_id, datasets=["test"])
            assert config.project_id == project_id

    def test_project_id_validator_invalid_format(self):
        """Test project ID validator rejects invalid formats."""
        invalid_ids = [
            "test@project",  # Invalid character
            "test.project",  # Invalid character
            "test project",  # Space
            "test!project",  # Special character
        ]

        for invalid_id in invalid_ids:
            with pytest.raises(ValidationError) as exc_info:
                ConnectionConfig(project_id=invalid_id, datasets=["test"])
            assert "Invalid GCP project ID format" in str(exc_info.value)

    def test_project_id_validator_length_validation(self):
        """Test project ID validator enforces length constraints."""
        # Too short
        with pytest.raises(ValidationError) as exc_info:
            ConnectionConfig(project_id="short", datasets=["test"])
        assert "must be between 6 and 30 characters" in str(exc_info.value)

        # Too long
        long_id = "a" * 31
        with pytest.raises(ValidationError) as exc_info:
            ConnectionConfig(project_id=long_id, datasets=["test"])
        assert "must be between 6 and 30 characters" in str(exc_info.value)

    def test_location_validator_none(self):
        """Test location validator with None value."""
        config = ConnectionConfig(datasets=["test"])
        assert config.location is None

    def test_location_validator_template_values(self):
        """Test location validator allows template values."""
        for template_location in ["your-region", "your-location"]:
            config = ConnectionConfig(
                location=template_location, datasets=["test"])
            assert config.location == template_location

    def test_location_validator_valid_locations(self):
        """Test location validator accepts valid BigQuery locations."""
        valid_locations = [
            "US",
            "EU",  # Multi-regional
            "us-central1",
            "europe-west1",
            "asia-east1",  # Regional
        ]

        for location in valid_locations:
            config = ConnectionConfig(location=location, datasets=["test"])
            assert config.location == location

    def test_location_validator_case_insensitive(self):
        """Test location validator handles case variations."""
        config = ConnectionConfig(location="us", datasets=["test"])
        assert config.location == "us"  # Should pass through even if not uppercase

    def test_location_validator_unknown_location(self):
        """Test location validator passes through unknown locations."""
        # Should not fail - BigQuery will handle validation
        config = ConnectionConfig(location="unknown-region", datasets=["test"])
        assert config.location == "unknown-region"

    def test_datasets_validator_empty_list(self):
        """Test datasets validator rejects empty lists."""
        with pytest.raises(ValidationError) as exc_info:
            ConnectionConfig(datasets=[])
        assert "List should have at least 1 item" in str(exc_info.value)

    def test_datasets_validator_empty_strings(self):
        """Test datasets validator rejects empty or whitespace-only names."""
        invalid_datasets = [
            ["", "valid_dataset"],
            ["   ", "valid_dataset"],
            ["valid_dataset", ""],
        ]

        for datasets in invalid_datasets:
            with pytest.raises(ValidationError) as exc_info:
                ConnectionConfig(datasets=datasets)
            assert "cannot be empty or whitespace only" in str(exc_info.value)

    def test_datasets_validator_invalid_names(self):
        """Test datasets validator rejects invalid dataset names."""
        invalid_datasets = [
            ["dataset-with-hyphens"],  # Hyphens not allowed
            ["dataset.with.dots"],  # Dots not allowed
            ["dataset with spaces"],  # Spaces not allowed
            ["dataset@special"],  # Special characters not allowed
        ]

        for datasets in invalid_datasets:
            with pytest.raises(ValidationError) as exc_info:
                ConnectionConfig(datasets=datasets)
            assert "must contain only letters, numbers, and underscores" in str(
                exc_info.value)

    def test_datasets_validator_valid_names(self):
        """Test datasets validator accepts valid dataset names."""
        valid_datasets = [
            ["raw_data", "staging_data"],
            ["analytics123", "reports_v2"],
            ["dataset1", "DATASET2"],
        ]

        for datasets in valid_datasets:
            config = ConnectionConfig(datasets=datasets)
            assert config.datasets == datasets


class TestLookerConfig:
    """Test LookerConfig validators and validation logic."""

    def test_valid_looker_config(self):
        """Test creation with valid configuration."""
        config = LookerConfig(
            project_path="./looker-project",
            views_path="views/generated.view.lkml",
            connection="bigquery_conn",
        )

        assert config.project_path == "./looker-project"
        assert config.views_path == "views/generated.view.lkml"
        assert config.connection == "bigquery_conn"

    def test_project_path_validator_empty(self):
        """Test project path validator rejects empty paths."""
        with pytest.raises(ValidationError) as exc_info:
            LookerConfig(
                project_path="",
                views_path="views/test.view.lkml",
                connection="test_conn",
            )
        assert "cannot be empty" in str(exc_info.value)

    def test_project_path_validator_whitespace_only(self):
        """Test project path validator rejects whitespace-only paths."""
        with pytest.raises(ValidationError) as exc_info:
            LookerConfig(
                project_path="   ",
                views_path="views/test.view.lkml",
                connection="test_conn",
            )
        assert "cannot be empty" in str(exc_info.value)

    def test_project_path_validator_template_values(self):
        """Test project path validator allows template values."""
        template_paths = [
            "path/to/your/looker/project",
            "./looker-project",
        ]

        for path in template_paths:
            config = LookerConfig(
                project_path=path,
                views_path="views/test.view.lkml",
                connection="test_conn",
            )
            assert config.project_path == path

    def test_project_path_validator_test_paths(self):
        """Test project path validator allows test paths."""
        test_paths = [
            "./test-project",
            "./looker-test",
            "./my-test-dir",
        ]

        for path in test_paths:
            config = LookerConfig(
                project_path=path,
                views_path="views/test.view.lkml",
                connection="test_conn",
            )
            assert config.project_path == path

    def test_project_path_validator_existing_directory(self):
        """Test project path validator accepts existing directories."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = LookerConfig(
                project_path=tmp_dir,
                views_path="views/test.view.lkml",
                connection="test_conn",
            )
            assert config.project_path == tmp_dir

    def test_project_path_validator_nonexistent_directory(self):
        """Test project path validator rejects non-existent directories."""
        with pytest.raises(ValidationError) as exc_info:
            LookerConfig(
                project_path="/nonexistent/directory",
                views_path="views/test.view.lkml",
                connection="test_conn",
            )
        assert "does not exist" in str(exc_info.value)

    def test_project_path_validator_file_not_directory(self):
        """Test project path validator rejects files."""
        with tempfile.NamedTemporaryFile() as tmp:
            with pytest.raises(ValidationError) as exc_info:
                LookerConfig(
                    project_path=tmp.name,
                    views_path="views/test.view.lkml",
                    connection="test_conn",
                )
            assert "is not a directory" in str(exc_info.value)

    def test_views_path_validator_empty(self):
        """Test views path validator rejects empty paths."""
        with pytest.raises(ValidationError) as exc_info:
            LookerConfig(
                project_path="./test",
                views_path="",
                connection="test_conn",
            )
        assert "cannot be empty" in str(exc_info.value)

    def test_views_path_validator_template_values(self):
        """Test views path validator allows template values."""
        config = LookerConfig(
            project_path="./test",
            views_path="views/concordia_views.view.lkml",
            connection="test_conn",
        )
        assert config.views_path == "views/concordia_views.view.lkml"

    def test_views_path_validator_test_files(self):
        """Test views path validator allows test files."""
        test_paths = [
            "test/views.lkml",
            "views/test_file.view.lkml",
            "test_views.txt",
        ]

        for path in test_paths:
            config = LookerConfig(
                project_path="./test",
                views_path=path,
                connection="test_conn",
            )
            assert config.views_path == path

    def test_views_path_validator_wrong_extension(self):
        """Test views path validator rejects non-.view.lkml files."""
        with pytest.raises(ValidationError) as exc_info:
            LookerConfig(
                project_path="./test",
                views_path="views/file.lkml",
                connection="test_conn",
            )
        assert "must end with '.view.lkml'" in str(exc_info.value)

    def test_views_path_validator_absolute_path(self):
        """Test views path validator rejects absolute paths."""
        import platform
        from pathlib import Path

        # Use appropriate absolute path for the current platform
        if platform.system() == "Windows":
            absolute_path = "C:\\absolute\\path\\views.view.lkml"
        else:
            absolute_path = "/absolute/path/views.view.lkml"

        # Verify our test path is actually absolute on this platform
        assert Path(absolute_path).is_absolute(
        ), f"Test path {absolute_path} should be absolute on {platform.system()}"

        with pytest.raises(ValidationError) as exc_info:
            LookerConfig(
                project_path="./test",
                views_path=absolute_path,
                connection="test_conn",
            )
        assert "must be relative" in str(exc_info.value)

    def test_connection_name_validator_empty(self):
        """Test connection name validator rejects empty names."""
        with pytest.raises(ValidationError) as exc_info:
            LookerConfig(
                project_path="./test",
                views_path="views/test.view.lkml",
                connection="",
            )
        assert "cannot be empty" in str(exc_info.value)

    def test_connection_name_validator_template_values(self):
        """Test connection name validator allows template values."""
        template_names = [
            "your-bigquery-connection",
            "your_connection_name",
        ]

        for name in template_names:
            config = LookerConfig(
                project_path="./test",
                views_path="views/test.view.lkml",
                connection=name,
            )
            assert config.connection == name

    def test_connection_name_validator_valid_names(self):
        """Test connection name validator accepts valid names."""
        valid_names = [
            "bigquery_connection",
            "prod-bigquery",
            "analytics_bq_123",
            "connection123",
        ]

        for name in valid_names:
            config = LookerConfig(
                project_path="./test",
                views_path="views/test.view.lkml",
                connection=name,
            )
            assert config.connection == name

    def test_connection_name_validator_invalid_names(self):
        """Test connection name validator rejects invalid names."""
        invalid_names = [
            "connection with spaces",
            "connection@special",
            "connection.dots",
            "connection!invalid",
        ]

        for name in invalid_names:
            with pytest.raises(ValidationError) as exc_info:
                LookerConfig(
                    project_path="./test",
                    views_path="views/test.view.lkml",
                    connection=name,
                )
            assert "Use only letters, numbers, underscores, and hyphens" in str(
                exc_info.value)


class TestTypeMapping:
    """Test TypeMapping validators and validation logic."""

    def test_valid_type_mapping(self):
        """Test creation with valid type mapping."""
        params = LookMLParams(type="dimension", sql="${TABLE}.${FIELD}")
        mapping = TypeMapping(
            bq_type="STRING",
            lookml_type="dimension",
            lookml_params=params,
        )

        assert mapping.bq_type == "STRING"
        assert mapping.lookml_type == "dimension"
        assert mapping.lookml_params.type == "dimension"

    def test_lookml_type_validator_valid_types(self):
        """Test lookml_type validator accepts valid types."""
        params = LookMLParams(type="dimension")
        valid_types = ["dimension", "dimension_group", "measure"]

        for lookml_type in valid_types:
            mapping = TypeMapping(
                bq_type="STRING",
                lookml_type=lookml_type,
                lookml_params=params,
            )
            assert mapping.lookml_type == lookml_type

    def test_lookml_type_validator_invalid_types(self):
        """Test lookml_type validator rejects invalid types."""
        params = LookMLParams(type="dimension")
        invalid_types = ["field", "parameter", "filter", "invalid"]

        for invalid_type in invalid_types:
            with pytest.raises(ValidationError) as exc_info:
                TypeMapping(
                    bq_type="STRING",
                    lookml_type=invalid_type,
                    lookml_params=params,
                )
            assert f"Invalid LookML type '{invalid_type}'" in str(
                exc_info.value)


class TestModelRules:
    """Test ModelRules validators and helper methods."""

    def test_valid_model_rules(self):
        """Test creation with valid model rules."""
        params = LookMLParams(type="dimension")
        mapping = TypeMapping(
            bq_type="STRING",
            lookml_type="dimension",
            lookml_params=params,
        )

        rules = ModelRules(type_mapping=[mapping])
        assert len(rules.type_mapping) == 1
        assert rules.type_mapping[0].bq_type == "STRING"

    def test_type_mapping_validator_empty_list(self):
        """Test type_mapping validator allows empty lists for testing."""
        rules = ModelRules(type_mapping=[])
        assert len(rules.type_mapping) == 0

    def test_get_type_mapping_for_bq_type_found(self):
        """Test get_type_mapping_for_bq_type returns correct mapping."""
        params = LookMLParams(type="dimension")
        string_mapping = TypeMapping(
            bq_type="STRING",
            lookml_type="dimension",
            lookml_params=params,
        )
        integer_mapping = TypeMapping(
            bq_type="INTEGER",
            lookml_type="dimension",
            lookml_params=params,
        )

        rules = ModelRules(type_mapping=[string_mapping, integer_mapping])

        found_mapping = rules.get_type_mapping_for_bq_type("STRING")
        assert found_mapping is not None
        assert found_mapping.bq_type == "STRING"

    def test_get_type_mapping_for_bq_type_not_found(self):
        """Test get_type_mapping_for_bq_type returns None for unknown types."""
        params = LookMLParams(type="dimension")
        mapping = TypeMapping(
            bq_type="STRING",
            lookml_type="dimension",
            lookml_params=params,
        )

        rules = ModelRules(type_mapping=[mapping])

        found_mapping = rules.get_type_mapping_for_bq_type("UNKNOWN_TYPE")
        assert found_mapping is None


class TestConcordiaConfig:
    """Test ConcordiaConfig model validator and overall configuration."""

    def create_valid_config(self) -> ConcordiaConfig:
        """Helper to create a valid configuration for testing."""
        connection = ConnectionConfig(datasets=["test_dataset"])
        looker = LookerConfig(
            project_path="./test",
            views_path="views/test.view.lkml",
            connection="test_conn",
        )

        params = LookMLParams(type="dimension")
        mapping = TypeMapping(
            bq_type="STRING",
            lookml_type="dimension",
            lookml_params=params,
        )
        model_rules = ModelRules(type_mapping=[mapping])

        return ConcordiaConfig(
            connection=connection,
            looker=looker,
            model_rules=model_rules,
        )

    def test_valid_concordia_config(self):
        """Test creation of valid ConcordiaConfig."""
        config = self.create_valid_config()

        assert config.connection.datasets == ["test_dataset"]
        assert config.looker.project_path == "./test"
        assert len(config.model_rules.type_mapping) == 1

    def test_config_to_dict(self):
        """Test to_dict method returns proper dictionary."""
        config = self.create_valid_config()
        config_dict = config.to_dict()

        assert isinstance(config_dict, dict)
        assert "connection" in config_dict
        assert "looker" in config_dict
        assert "model_rules" in config_dict

    def test_config_from_dict(self):
        """Test from_dict class method creates valid config."""
        config = self.create_valid_config()
        config_dict = config.to_dict()

        recreated_config = ConcordiaConfig.from_dict(config_dict)

        assert recreated_config.connection.datasets == config.connection.datasets
        assert recreated_config.looker.project_path == config.looker.project_path
        assert len(recreated_config.model_rules.type_mapping) == len(
            config.model_rules.type_mapping)

    def test_validate_config_consistency_existing_looker_path(self):
        """Test model validator with existing Looker project path."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            connection = ConnectionConfig(datasets=["test_dataset"])
            looker = LookerConfig(
                project_path=tmp_dir,
                views_path="views/test.view.lkml",
                connection="test_conn",
            )

            params = LookMLParams(type="dimension")
            mapping = TypeMapping(
                bq_type="STRING",
                lookml_type="dimension",
                lookml_params=params,
            )
            model_rules = ModelRules(type_mapping=[mapping])

            # Should create views directory if it doesn't exist
            ConcordiaConfig(
                connection=connection,
                looker=looker,
                model_rules=model_rules,
            )

            views_dir = Path(tmp_dir) / "views"
            assert views_dir.exists()

    def test_validate_config_consistency_creates_missing_views_directory(self):
        """Test model validator creates missing views directory when possible."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create nested directory structure
            views_dir = Path(tmp_dir) / "views"
            # Don't create views directory initially

            connection = ConnectionConfig(datasets=["test_dataset"])
            looker = LookerConfig(
                project_path=tmp_dir,
                views_path="views/test.view.lkml",
                connection="test_conn",
            )

            params = LookMLParams(type="dimension")
            mapping = TypeMapping(
                bq_type="STRING",
                lookml_type="dimension",
                lookml_params=params,
            )
            model_rules = ModelRules(type_mapping=[mapping])

            # Should succeed and create the views directory
            ConcordiaConfig(
                connection=connection,
                looker=looker,
                model_rules=model_rules,
            )

            # Verify the directory was created
            assert views_dir.exists()
            assert views_dir.is_dir()


class TestNamingConventions:
    """Test NamingConventions model."""

    def test_default_naming_conventions(self):
        """Test default values for naming conventions."""
        conventions = NamingConventions()

        assert conventions.pk_suffix == "_pk"
        assert conventions.fk_suffix == "_fk"
        assert conventions.view_prefix == ""
        assert conventions.view_suffix == ""

    def test_custom_naming_conventions(self):
        """Test custom naming conventions."""
        conventions = NamingConventions(
            pk_suffix="_id",
            fk_suffix="_ref",
            view_prefix="bq_",
            view_suffix="_view",
        )

        assert conventions.pk_suffix == "_id"
        assert conventions.fk_suffix == "_ref"
        assert conventions.view_prefix == "bq_"
        assert conventions.view_suffix == "_view"


class TestDefaultBehaviors:
    """Test DefaultBehaviors model."""

    def test_default_behaviors(self):
        """Test default values for behaviors."""
        behaviors = DefaultBehaviors()

        assert behaviors.measures == ["count"]
        assert behaviors.hide_fields_by_suffix == ["_pk", "_fk"]

    def test_custom_behaviors(self):
        """Test custom behavior configuration."""
        behaviors = DefaultBehaviors(
            measures=[],
            hide_fields_by_suffix=["_id", "_key"],
        )

        assert behaviors.measures == []
        assert behaviors.hide_fields_by_suffix == ["_id", "_key"]


class TestLookMLParams:
    """Test LookMLParams model with extra fields allowed."""

    def test_basic_lookml_params(self):
        """Test basic LookML parameters."""
        params = LookMLParams(type="dimension")

        assert params.type == "dimension"
        assert params.timeframes is None
        assert params.sql is None

    def test_lookml_params_with_optional_fields(self):
        """Test LookML parameters with optional fields."""
        params = LookMLParams(
            type="dimension_group",
            timeframes="time,date,week,month",
            sql="${TABLE}.${FIELD}",
        )

        assert params.type == "dimension_group"
        assert params.timeframes == "time,date,week,month"
        assert params.sql == "${TABLE}.${FIELD}"

    def test_lookml_params_extra_fields_allowed(self):
        """Test that extra fields are allowed due to model_config."""
        # This should work because of `extra: "allow"` in the model config
        params = LookMLParams(
            type="dimension",
            custom_field="custom_value",
            another_field=123,
        )

        assert params.type == "dimension"
        # Extra fields should be accessible
        assert hasattr(params, "custom_field")
        assert hasattr(params, "another_field")
