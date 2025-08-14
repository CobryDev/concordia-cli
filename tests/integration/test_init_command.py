"""
Integration tests for the init command.

Tests file creation, project detection, error handling, and end-to-end
initialization functionality.
"""

import os
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, Mock
from click.testing import CliRunner

from main import cli
from actions.init.initialization import (
    run_initialization,
    find_file_in_tree,
    handle_gitignore,
    scan_for_projects,
    create_configuration_file,
)


class TestInitCommandIntegration:
    """Integration tests for the init command."""

    def setup_method(self):
        """Set up test environment for each test."""
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        self.runner = CliRunner()

    def teardown_method(self):
        """Clean up test environment after each test."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)

    def test_init_command_basic_execution(self):
        """Test basic init command execution."""
        # Mock user confirmation
        with patch("click.confirm", return_value=True):
            result = self.runner.invoke(cli, ["init"])

        assert result.exit_code == 0
        assert "Concordia initialization complete!" in result.output
        assert os.path.exists("concordia.yaml")
        assert os.path.exists(".gitignore")

    def test_init_command_with_force_flag(self):
        """Test init command with --force flag."""
        # Create existing concordia.yaml
        with open("concordia.yaml", "w") as f:
            f.write("existing: config")

        with patch("click.confirm", return_value=True):
            result = self.runner.invoke(cli, ["init", "--force"])

        assert result.exit_code == 0
        assert os.path.exists("concordia.yaml")

        # Check that file was overwritten
        with open("concordia.yaml", "r") as f:
            content = f.read()
            assert "existing: config" not in content
            assert "connection:" in content

    def test_init_command_without_force_existing_file(self):
        """Test init command fails when file exists without --force."""
        # Create existing concordia.yaml
        with open("concordia.yaml", "w") as f:
            f.write("existing: config")

        result = self.runner.invoke(cli, ["init"])

        assert result.exit_code == 0  # Command completes but doesn't overwrite
        assert "already exists" in result.output

        # Check that file was not overwritten
        with open("concordia.yaml", "r") as f:
            content = f.read()
            assert "existing: config" in content

    def test_init_command_user_cancellation(self):
        """Test init command when user cancels."""
        with patch("click.confirm", return_value=False):
            result = self.runner.invoke(cli, ["init"])

        assert result.exit_code == 0
        assert "Initialization cancelled" in result.output
        assert not os.path.exists("concordia.yaml")

    def test_init_with_dataform_project_detection(self):
        """Test init command with Dataform project auto-detection."""
        # Create workflow_settings.yaml to simulate Dataform project
        with open("workflow_settings.yaml", "w") as f:
            f.write("defaultProject: test-project")

        with patch("click.confirm", return_value=True):
            result = self.runner.invoke(cli, ["init"])

        assert result.exit_code == 0
        assert "Found Dataform project" in result.output
        assert os.path.exists("concordia.yaml")

        # Check config contains correct dataform path
        with open("concordia.yaml", "r") as f:
            content = f.read()
            assert ".df-credentials.json" in content

    def test_init_with_looker_project_detection(self):
        """Test init command with Looker project auto-detection."""
        # Create manifest.lkml in subdirectory
        looker_dir = Path("looker_project")
        looker_dir.mkdir()
        (looker_dir / "manifest.lkml").write_text('project_name: "test_project"')

        with patch("click.confirm", return_value=True):
            result = self.runner.invoke(cli, ["init"])

        assert result.exit_code == 0
        assert "Found Looker project" in result.output
        assert os.path.exists("concordia.yaml")

        # Check config contains correct looker path (normalize path separators)
        with open("concordia.yaml", "r") as f:
            content = f.read()
            # Check that looker_project is mentioned in the path, regardless of path format
            assert "looker_project" in content

    def test_init_with_both_projects_detected(self):
        """Test init command with both Dataform and Looker projects."""
        # Create both project indicators
        with open("workflow_settings.yaml", "w") as f:
            f.write("defaultProject: test-project")

        looker_dir = Path("looker")
        looker_dir.mkdir()
        (looker_dir / "manifest.lkml").write_text('project_name: "test"')

        with patch("click.confirm", return_value=True):
            result = self.runner.invoke(cli, ["init"])

        assert result.exit_code == 0
        assert "Found Dataform project" in result.output
        assert "Found Looker project" in result.output

        # Check config contains both paths
        with open("concordia.yaml", "r") as f:
            content = f.read()
            assert ".df-credentials.json" in content
            # Check that looker directory is mentioned in the path, regardless of path format
            assert "looker" in content

    def test_init_error_handling_permission_error(self):
        """Test init command handles permission errors gracefully."""
        # Mock file write to raise permission error
        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            with patch("click.confirm", return_value=True):
                result = self.runner.invoke(cli, ["init"])

        assert result.exit_code != 0
        assert "Error during initialization" in result.output

    def test_gitignore_creation_new_file(self):
        """Test .gitignore creation when file doesn't exist."""
        handle_gitignore()

        assert os.path.exists(".gitignore")
        with open(".gitignore", "r") as f:
            content = f.read()
            assert ".df-credentials.json" in content
            assert "Dataform credentials" in content

    def test_gitignore_update_existing_file(self):
        """Test .gitignore update when file exists."""
        # Create existing .gitignore
        with open(".gitignore", "w") as f:
            f.write("*.log\n__pycache__/\n")

        handle_gitignore()

        with open(".gitignore", "r") as f:
            content = f.read()
            assert "*.log" in content
            assert "__pycache__/" in content
            assert ".df-credentials.json" in content

    def test_gitignore_no_duplicate_entries(self):
        """Test .gitignore doesn't add duplicate entries."""
        # Create .gitignore with existing entry
        with open(".gitignore", "w") as f:
            f.write(".df-credentials.json\n")

        handle_gitignore()

        with open(".gitignore", "r") as f:
            content = f.read()
            assert content.count(".df-credentials.json") == 1


class TestInitHelperFunctions:
    """Test helper functions used by the init command."""

    def setup_method(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)

    def teardown_method(self):
        """Clean up test environment."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)

    def test_find_file_in_tree_found(self):
        """Test find_file_in_tree when file is found."""
        # Create nested directory structure
        nested_dir = Path("a/b/c")
        nested_dir.mkdir(parents=True)
        (nested_dir / "target.txt").write_text("content")

        result = find_file_in_tree("target.txt")
        # Normalize paths for cross-platform comparison
        expected = str(nested_dir).replace("\\", "/")
        actual = result.replace("\\", "/") if result else None
        assert actual == expected

    def test_find_file_in_tree_not_found(self):
        """Test find_file_in_tree when file is not found."""
        result = find_file_in_tree("nonexistent.txt")
        assert result is None

    def test_find_file_in_tree_multiple_files(self):
        """Test find_file_in_tree returns first match."""
        # Create multiple directories with same filename
        dir1 = Path("dir1")
        dir2 = Path("dir2")
        dir1.mkdir()
        dir2.mkdir()

        (dir1 / "manifest.lkml").write_text("content1")
        (dir2 / "manifest.lkml").write_text("content2")

        result = find_file_in_tree("manifest.lkml")
        # Normalize result for cross-platform comparison and get just the directory name
        if result:
            result_normalized = result.replace("\\", "/").split("/")[-1]
        else:
            result_normalized = None
        assert result_normalized in ["dir1", "dir2"]  # Either is valid

    def test_scan_for_projects_no_projects(self):
        """Test scan_for_projects when no projects found."""
        dataform_path, looker_path = scan_for_projects()

        assert dataform_path is None
        assert looker_path is None

    def test_scan_for_projects_dataform_only(self):
        """Test scan_for_projects with only Dataform project."""
        with open("workflow_settings.yaml", "w") as f:
            f.write("defaultProject: test")

        dataform_path, looker_path = scan_for_projects()

        assert dataform_path == "."
        assert looker_path is None

    def test_scan_for_projects_looker_only(self):
        """Test scan_for_projects with only Looker project."""
        looker_dir = Path("looker")
        looker_dir.mkdir()
        (looker_dir / "manifest.lkml").write_text('project_name: "test"')

        dataform_path, looker_path = scan_for_projects()

        assert dataform_path is None
        # Normalize result for cross-platform comparison and get just the directory name
        if looker_path:
            looker_normalized = looker_path.replace("\\", "/").split("/")[-1]
        else:
            looker_normalized = None
        assert looker_normalized == "looker"

    def test_create_configuration_file_with_paths(self):
        """Test configuration file creation with project paths."""
        create_configuration_file(".", "looker", "test_config.yaml")

        assert os.path.exists("test_config.yaml")

        with open("test_config.yaml", "r") as f:
            content = f.read()
            assert "connection:" in content
            assert "looker:" in content
            assert "model_rules:" in content
            assert ".df-credentials.json" in content
            assert "./looker/" in content

    def test_create_configuration_file_without_paths(self):
        """Test configuration file creation without project paths."""
        create_configuration_file(None, None, "test_config.yaml")

        assert os.path.exists("test_config.yaml")

        with open("test_config.yaml", "r") as f:
            content = f.read()
            assert "path/to/your/.df-credentials.json" in content
            assert "path/to/your/looker_project" in content


class TestInitCommandErrorScenarios:
    """Test error scenarios and edge cases for init command."""

    def setup_method(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        self.runner = CliRunner()

    def teardown_method(self):
        """Clean up test environment."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)

    def test_init_command_yaml_generation_error(self):
        """Test init command when YAML generation fails."""
        with patch(
            "actions.init.initialization.generate_concordia_config",
            side_effect=Exception("YAML error"),
        ):
            with patch("click.confirm", return_value=True):
                result = self.runner.invoke(cli, ["init"])

        assert result.exit_code != 0
        assert "Error during initialization" in result.output

    def test_init_command_gitignore_permission_error(self):
        """Test init command when .gitignore creation fails."""
        # Create a directory named .gitignore to cause error
        os.mkdir(".gitignore")

        with patch("click.confirm", return_value=True):
            result = self.runner.invoke(cli, ["init"])

        # Command should fail due to gitignore error
        assert result.exit_code != 0

    @pytest.mark.slow
    def test_init_command_with_deep_directory_structure(self):
        """Test init with very deep directory structure."""
        # Create deep nested structure
        deep_path = Path("a/b/c/d/e/f/g/h/i/j")
        deep_path.mkdir(parents=True)
        (deep_path / "manifest.lkml").write_text('project_name: "deep"')

        with patch("click.confirm", return_value=True):
            result = self.runner.invoke(cli, ["init"])

        assert result.exit_code == 0
        assert "Found Looker project" in result.output

    def test_init_command_with_readonly_directory(self):
        """Test init command in read-only directory."""
        # Make directory read-only (skip on Windows where this is complex)
        if os.name != "nt":
            os.chmod(self.test_dir, 0o444)

            with patch("click.confirm", return_value=True):
                result = self.runner.invoke(cli, ["init"])

            # Should handle permission error gracefully by reporting failure
            assert result.exit_code != 0
            # The permission error might manifest differently depending on when it occurs
            assert (
                "No Dataform project found" in result.output
                or "Error during initialization" in result.output
            )

            # Restore permissions for cleanup
            os.chmod(self.test_dir, 0o755)
