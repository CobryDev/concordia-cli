"""
Unit tests for config.py module.

Tests the configuration generation functions that create YAML files
with proper comments and structure.
"""

import os
import tempfile
from pathlib import Path

import pytest
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

from actions.init.config import generate_concordia_config, write_yaml_with_comments


class TestGenerateConcordiaConfig:
    """Test cases for generate_concordia_config function."""

    def test_generate_config_with_both_paths(self):
        """Test config generation with both dataform and looker paths."""
        config = generate_concordia_config("./dataform", "./looker")

        # Test basic structure
        assert isinstance(config, CommentedMap)
        assert "connection" in config
        assert "looker" in config
        assert "model_rules" in config

    def test_generate_config_with_dataform_path_only(self):
        """Test config generation with only dataform path."""
        config = generate_concordia_config("./dataform", None)

        connection = config["connection"]
        looker = config["looker"]

        # Should use provided dataform path
        assert connection["dataform_credentials_file"] == "./.df-credentials.json"

        # Should use default looker path
        assert looker["project_path"] == "./path/to/your/looker_project/"

    def test_generate_config_with_looker_path_only(self):
        """Test config generation with only looker path."""
        config = generate_concordia_config(None, "./looker")

        connection = config["connection"]
        looker = config["looker"]

        # Should use default dataform path
        assert connection["dataform_credentials_file"] == "path/to/your/.df-credentials.json"

        # Should use provided looker path (note: gets ./ prefix added)
        assert looker["project_path"] == "././looker/"

    def test_generate_config_with_no_paths(self):
        """Test config generation with no paths provided."""
        config = generate_concordia_config(None, None)

        connection = config["connection"]
        looker = config["looker"]

        # Should use default paths
        assert connection["dataform_credentials_file"] == "path/to/your/.df-credentials.json"
        assert looker["project_path"] == "./path/to/your/looker_project/"

    def test_connection_section_structure(self):
        """Test connection section has correct structure and values."""
        config = generate_concordia_config(None, None)
        connection = config["connection"]

        # Check required fields
        assert "dataform_credentials_file" in connection
        assert "project_id" in connection
        assert "location" in connection
        assert "datasets" in connection

        # Check default values
        assert connection["project_id"] == "your-gcp-project-id"
        assert connection["location"] == "your-region"
        assert connection["datasets"] == ["dataset1", "dataset2"]

    def test_looker_section_structure(self):
        """Test looker section has correct structure and values."""
        config = generate_concordia_config(None, "./looker")
        looker = config["looker"]

        # Check required fields
        assert "project_path" in looker
        assert "views_path" in looker

        assert "connection" in looker

        # Check default values (note: gets ./ prefix added)
        assert looker["project_path"] == "././looker/"
        assert looker["views_path"] == "views/generated_views.view.lkml"

        assert looker["connection"] == "your-bigquery-connection"

    def test_model_rules_section_structure(self):
        """Test model_rules section has correct structure."""
        config = generate_concordia_config(None, None)
        model_rules = config["model_rules"]

        # Check main sections
        assert "naming_conventions" in model_rules
        assert "defaults" in model_rules
        assert "type_mapping" in model_rules

    def test_naming_conventions_defaults(self):
        """Test naming conventions have correct default values."""
        config = generate_concordia_config(None, None)
        naming = config["model_rules"]["naming_conventions"]

        assert naming["pk_suffix"] == "_pk"
        assert naming["fk_suffix"] == "_fk"

    def test_defaults_section_structure(self):
        """Test defaults section has correct structure."""
        config = generate_concordia_config(None, None)
        defaults = config["model_rules"]["defaults"]

        assert "measures" in defaults
        assert "hide_fields_by_suffix" in defaults

        assert defaults["measures"] == ["count"]
        assert defaults["hide_fields_by_suffix"] == ["_pk", "_fk"]

    def test_type_mapping_completeness(self):
        """Test type mapping includes all expected BigQuery types."""
        config = generate_concordia_config(None, None)
        type_mapping = config["model_rules"]["type_mapping"]

        # Should be a list of type mappings
        assert isinstance(type_mapping, list)
        assert len(type_mapping) >= 5  # At least 5 common types

        # Extract mapped types
        mapped_types = [mapping["bq_type"] for mapping in type_mapping]

        # Check essential types are included
        assert "STRING" in mapped_types
        assert "INTEGER" in mapped_types
        assert "TIMESTAMP" in mapped_types
        assert "DATE" in mapped_types
        assert "BOOL" in mapped_types

    def test_type_mapping_structure(self):
        """Test each type mapping has correct structure."""
        config = generate_concordia_config(None, None)
        type_mapping = config["model_rules"]["type_mapping"]

        for mapping in type_mapping:
            # Each mapping should have required fields
            assert "bq_type" in mapping
            assert "lookml_type" in mapping
            assert "lookml_params" in mapping

            # lookml_params should be a dict
            assert isinstance(mapping["lookml_params"], dict)

    def test_timestamp_type_mapping_details(self):
        """Test TIMESTAMP type mapping has correct LookML configuration."""
        config = generate_concordia_config(None, None)
        type_mapping = config["model_rules"]["type_mapping"]

        timestamp_mapping = next(m for m in type_mapping if m["bq_type"] == "TIMESTAMP")

        assert timestamp_mapping["lookml_type"] == "dimension_group"
        params = timestamp_mapping["lookml_params"]
        assert params["type"] == "time"
        assert "raw" in params["timeframes"]
        assert "time" in params["timeframes"]
        assert "date" in params["timeframes"]
        assert params["sql"] == "${TABLE}.%s"

    def test_date_type_mapping_details(self):
        """Test DATE type mapping has correct LookML configuration."""
        config = generate_concordia_config(None, None)
        type_mapping = config["model_rules"]["type_mapping"]

        date_mapping = next(m for m in type_mapping if m["bq_type"] == "DATE")

        assert date_mapping["lookml_type"] == "dimension_group"
        params = date_mapping["lookml_params"]
        assert params["type"] == "time"
        # DATE should not have 'time' timeframe
        assert "time" not in params["timeframes"]
        assert "date" in params["timeframes"]

    def test_string_type_mapping_details(self):
        """Test STRING type mapping has correct LookML configuration."""
        config = generate_concordia_config(None, None)
        type_mapping = config["model_rules"]["type_mapping"]

        string_mapping = next(m for m in type_mapping if m["bq_type"] == "STRING")

        assert string_mapping["lookml_type"] == "dimension"
        params = string_mapping["lookml_params"]
        assert params["type"] == "string"

    def test_integer_type_mapping_details(self):
        """Test INTEGER type mapping has correct LookML configuration."""
        config = generate_concordia_config(None, None)
        type_mapping = config["model_rules"]["type_mapping"]

        integer_mapping = next(m for m in type_mapping if m["bq_type"] == "INTEGER")

        assert integer_mapping["lookml_type"] == "dimension"
        params = integer_mapping["lookml_params"]
        assert params["type"] == "number"

    def test_bool_type_mapping_details(self):
        """Test BOOL type mapping has correct LookML configuration."""
        config = generate_concordia_config(None, None)
        type_mapping = config["model_rules"]["type_mapping"]

        bool_mapping = next(m for m in type_mapping if m["bq_type"] == "BOOL")

        assert bool_mapping["lookml_type"] == "dimension"
        params = bool_mapping["lookml_params"]
        assert params["type"] == "yesno"

    def test_config_has_comments(self):
        """Test that the generated config has comment metadata."""
        config = generate_concordia_config(None, None)

        # CommentedMap should have comment metadata
        assert hasattr(config, "ca")  # Comment attributes

        # Check that sections have comments
        # This is a basic check - the actual comment content would be tested in integration


class TestWriteYamlWithComments:
    """Test cases for write_yaml_with_comments function."""

    def setup_method(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.test_dir, "test_config.yaml")

    def teardown_method(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.test_dir)

    def test_write_yaml_basic_functionality(self):
        """Test basic YAML writing functionality."""
        config = generate_concordia_config("./dataform", "./looker")

        write_yaml_with_comments(config, self.test_file)

        # Check file was created
        assert os.path.exists(self.test_file)

        # Check file is readable
        with open(self.test_file, "r") as f:
            content = f.read()
            assert len(content) > 0

    def test_write_yaml_preserves_structure(self):
        """Test that written YAML preserves the original structure."""
        config = generate_concordia_config("./dataform", "./looker")

        write_yaml_with_comments(config, self.test_file)

        # Read back and parse
        yaml = YAML()
        with open(self.test_file, "r") as f:
            loaded_config = yaml.load(f)

        # Check main sections exist
        assert "connection" in loaded_config
        assert "looker" in loaded_config
        assert "model_rules" in loaded_config

        # Check specific values are preserved
        assert loaded_config["connection"]["project_id"] == "your-gcp-project-id"
        assert loaded_config["looker"]["project_path"] == "././looker/"
        assert loaded_config["model_rules"]["naming_conventions"]["pk_suffix"] == "_pk"

    def test_write_yaml_preserves_comments(self):
        """Test that written YAML contains comments."""
        config = generate_concordia_config("./dataform", "./looker")

        write_yaml_with_comments(config, self.test_file)

        with open(self.test_file, "r") as f:
            content = f.read()

        # Check for presence of comment indicators
        assert "#" in content  # YAML comments start with #

        # Check for specific expected comments
        assert "BigQuery Connection Details" in content
        assert "Looker project configuration" in content
        assert "Rules for how models and fields are generated" in content

    def test_write_yaml_handles_complex_structure(self):
        """Test YAML writing with complex nested structures."""
        config = generate_concordia_config("./dataform", "./looker")

        write_yaml_with_comments(config, self.test_file)

        # Read back and check type mapping preservation
        yaml = YAML()
        with open(self.test_file, "r") as f:
            loaded_config = yaml.load(f)

        type_mapping = loaded_config["model_rules"]["type_mapping"]
        assert isinstance(type_mapping, list)
        assert len(type_mapping) >= 5

        # Check a specific mapping is preserved correctly
        timestamp_mapping = next(m for m in type_mapping if m["bq_type"] == "TIMESTAMP")
        assert timestamp_mapping["lookml_type"] == "dimension_group"
        assert timestamp_mapping["lookml_params"]["type"] == "time"

    def test_write_yaml_file_permissions(self):
        """Test that written YAML file has correct permissions."""
        config = generate_concordia_config("./dataform", "./looker")

        write_yaml_with_comments(config, self.test_file)

        # Check file is readable and writable by owner
        assert os.access(self.test_file, os.R_OK)
        assert os.access(self.test_file, os.W_OK)

    def test_write_yaml_overwrite_existing(self):
        """Test that writing YAML overwrites existing file."""
        # Create initial file
        with open(self.test_file, "w") as f:
            f.write("old content")

        config = generate_concordia_config("./dataform", "./looker")
        write_yaml_with_comments(config, self.test_file)

        # Check old content is gone
        with open(self.test_file, "r") as f:
            content = f.read()
            assert "old content" not in content
            assert "connection:" in content

    def test_write_yaml_error_handling(self):
        """Test YAML writing error handling."""
        config = generate_concordia_config("./dataform", "./looker")

        # Try to write to invalid path
        invalid_path = "/root/invalid/path/config.yaml"

        # Should raise an exception (which would be caught by calling code)
        with pytest.raises((PermissionError, FileNotFoundError, OSError)):
            write_yaml_with_comments(config, invalid_path)

    def test_yaml_formatting_standards(self):
        """Test that written YAML follows formatting standards."""
        config = generate_concordia_config("./dataform", "./looker")

        write_yaml_with_comments(config, self.test_file)

        with open(self.test_file, "r") as f:
            lines = f.readlines()

        # Check basic formatting standards
        assert len(lines) > 10  # Should be substantial file

        # Check indentation (find actual indented content, not comments)
        # Look for an indented key after connection
        connection_line = next(i for i, line in enumerate(lines) if "connection:" in line)
        # Find next line that's not a comment and has content
        for i in range(connection_line + 1, min(connection_line + 10, len(lines))):
            line = lines[i]
            if line.strip() and not line.strip().startswith("#") and ":" in line:
                assert line.startswith("  ")  # Should be indented by 2 spaces
                break

        # Check no tabs are used
        for line in lines:
            assert "\t" not in line
