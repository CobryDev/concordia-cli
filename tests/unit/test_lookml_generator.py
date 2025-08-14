"""
Unit tests for the lookml_generator module.
"""

import pytest
import tempfile
import os
import lkml
from pathlib import Path
from unittest.mock import Mock, patch
from actions.looker.lookml_generator import LookMLGenerator, LookMLFileWriter
from actions.models.config import (
    ConcordiaConfig,
    ConnectionConfig,
    LookerConfig,
    ModelRules,
    NamingConventions,
    DefaultBehaviors,
    TypeMapping,
    LookMLParams,
)


class TestLookMLGenerator:
    """Test LookML generator functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = {
            "looker": {
                "project_path": "./test_looker",
                "views_path": "views/test.view.lkml",
                "connection": "test_connection",
            },
            "model_rules": {
                "naming_conventions": {
                    "view_prefix": "",
                    "view_suffix": "",
                }
            },
        }


class TestLookMLFileWriter:
    """Test LookML file writer functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        from actions.models.config import (
            ConcordiaConfig,
            ConnectionConfig,
            LookerConfig,
            ModelRules,
        )

        self.config = ConcordiaConfig(
            connection=ConnectionConfig(project_id="test-project", datasets=["test"]),
            looker=LookerConfig(
                project_path=self.temp_dir,
                views_path="views/test.view.lkml",
                connection="test-connection",
            ),
            model_rules=ModelRules(
                naming_conventions=NamingConventions(pk_suffix="_pk", fk_suffix="_fk"),
                defaults=DefaultBehaviors(
                    measures=["count"], hide_fields_by_suffix=["_pk"]
                ),
                type_mapping=[
                    TypeMapping(
                        bq_type="STRING",
                        lookml_type="dimension",
                        lookml_params=LookMLParams(type="string"),
                    )
                ],
            ),
        )

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_write_views_file(self):
        """Test writing views to a file."""
        writer = LookMLFileWriter(self.config)

        view_contents = [
            "view: test_view1 {\n  dimension: id { type: number }\n}",
            "view: test_view2 {\n  dimension: name { type: string }\n}",
        ]

        file_path = writer.write_views_file(view_contents)

        # Verify file was created
        assert os.path.exists(file_path)

        # Verify content
        with open(file_path, "r") as f:
            content = f.read()

        assert "test_view1" in content
        assert "test_view2" in content
        assert "\n\n" in content  # Views should be separated by double newlines

    def test_write_lookml_dict_file_views(self):
        """Test writing LookML dictionary to views file."""
        writer = LookMLFileWriter(self.config)

        lookml_dict = {"view": {"test_view": {"dimension": {"id": {"type": "number"}}}}}

        file_path = writer.write_lookml_dict_file(lookml_dict, "views")

        # Verify file was created
        assert os.path.exists(file_path)

        # Verify it's a valid LookML file
        with open(file_path, "r") as f:
            content = f.read()

        assert "view:" in content

    def test_write_views_dict_file(self):
        """Test writing views dictionary to file."""
        writer = LookMLFileWriter(self.config)

        views_dict = {"test_view": {"dimension": {"id": {"type": "number"}}}}

        file_path = writer.write_views_dict_file(views_dict)

        # Verify file was created
        assert os.path.exists(file_path)

    def test_write_complete_project(self):
        """Test writing complete project with views only."""
        writer = LookMLFileWriter(self.config)

        project_dict = {
            "view": {"test_view": {"dimension": {"id": {"type": "number"}}}}
        }

        written_files = writer.write_complete_project(project_dict)

        # Verify one file was created
        assert len(written_files) == 1

        for file_path in written_files:
            assert os.path.exists(file_path)
