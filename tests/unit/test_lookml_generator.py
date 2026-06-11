"""
Unit tests for the lookml_generator module.
"""

import os
import tempfile

import pytest

from actions.looker.lookml_generator import DuplicateViewNameError, LookMLFileWriter, LookMLGenerator
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
from actions.models.metadata import ColumnMetadata, MetadataCollection, TableMetadata


class TestLookMLGenerator:
    """Test LookML generator functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = ConcordiaConfig(
            connection=ConnectionConfig(project_id="test-project", datasets=["test"]),
            looker=LookerConfig(
                project_path="./test_looker",
                views_path="views/test.view.lkml",
                connection="test_connection",
            ),
            model_rules=ModelRules(
                naming_conventions=NamingConventions(pk_suffix="_pk", fk_suffix="_fk"),
                defaults=DefaultBehaviors(measures=["count"], hide_fields_by_suffix=["_pk"]),
                type_mapping=[
                    TypeMapping(
                        bq_type="STRING",
                        lookml_type="dimension",
                        lookml_params=LookMLParams(type="string"),
                    ),
                    TypeMapping(
                        bq_type="INTEGER",
                        lookml_type="dimension",
                        lookml_params=LookMLParams(type="number"),
                    ),
                ],
            ),
        )

    def test_generate_complete_lookml_project_raises_error_on_duplicate_view_names(self):
        """Test that duplicate view names raise DuplicateViewNameError with details."""
        generator = LookMLGenerator(self.config)

        # Create two tables with the same table_id but different dataset_ids
        table1 = TableMetadata(
            table_id="users",
            dataset_id="dataset1",
            project_id="test-project",
            columns=[
                ColumnMetadata(
                    name="id",
                    type="INTEGER",
                    standardized_type="INTEGER",
                    is_primary_key=True,
                ),
                ColumnMetadata(
                    name="email",
                    type="STRING",
                    standardized_type="STRING",
                ),
            ],
        )

        table2 = TableMetadata(
            table_id="users",
            dataset_id="dataset2",
            project_id="test-project",
            columns=[
                ColumnMetadata(
                    name="id",
                    type="INTEGER",
                    standardized_type="INTEGER",
                    is_primary_key=True,
                ),
                ColumnMetadata(
                    name="name",
                    type="STRING",
                    standardized_type="STRING",
                ),
            ],
        )

        # Create metadata collection
        metadata_collection = MetadataCollection(
            tables={
                "dataset1.users": table1,
                "dataset2.users": table2,
            }
        )

        # Generate project should raise DuplicateViewNameError
        with pytest.raises(DuplicateViewNameError) as exc_info:
            generator.generate_complete_lookml_project(metadata_collection)

        # Verify error details
        error = exc_info.value
        assert error.view_name == "users"
        assert len(error.conflicting_tables) == 2

        # Verify error message contains table information
        error_message = str(error)
        assert "users" in error_message
        assert "test-project.dataset1.users" in error_message
        assert "test-project.dataset2.users" in error_message
        assert "Looker requires view names to be unique" in error_message
        assert "Generate only one of the conflicting objects" in error_message

    def test_generate_complete_lookml_project_raises_error_on_triple_duplicate_view_names(self):
        """Test that three tables with same table_id raise error with all conflicting tables."""
        generator = LookMLGenerator(self.config)

        # Create three tables with the same table_id but different dataset_ids
        tables = []
        for dataset_id in ["dataset1", "dataset2", "dataset3"]:
            table = TableMetadata(
                table_id="orders",
                dataset_id=dataset_id,
                project_id="test-project",
                columns=[
                    ColumnMetadata(
                        name="id",
                        type="INTEGER",
                        standardized_type="INTEGER",
                        is_primary_key=True,
                    ),
                ],
            )
            tables.append((f"{dataset_id}.orders", table))

        # Create metadata collection
        metadata_collection = MetadataCollection(tables=dict(tables))

        # Generate project should raise DuplicateViewNameError
        with pytest.raises(DuplicateViewNameError) as exc_info:
            generator.generate_complete_lookml_project(metadata_collection)

        # Verify error details
        error = exc_info.value
        assert error.view_name == "orders"
        assert len(error.conflicting_tables) == 3

        # Verify all three tables are in the error message
        error_message = str(error)
        assert "test-project.dataset1.orders" in error_message
        assert "test-project.dataset2.orders" in error_message
        assert "test-project.dataset3.orders" in error_message

    def test_generate_complete_lookml_project_raises_error_on_sanitized_duplicate_view_names(self):
        """Test that names colliding after character replacements are rejected."""
        self.config.model_rules.naming_conventions.character_replacements = {"-": "_"}
        generator = LookMLGenerator(self.config)

        table1 = TableMetadata(
            table_id="Order-Items",
            dataset_id="dataset1",
            project_id="test-project",
            columns=[
                ColumnMetadata(
                    name="id",
                    type="INTEGER",
                    standardized_type="INTEGER",
                    is_primary_key=True,
                )
            ],
        )
        table2 = TableMetadata(
            table_id="order_items",
            dataset_id="dataset2",
            project_id="test-project",
            columns=[
                ColumnMetadata(
                    name="id",
                    type="INTEGER",
                    standardized_type="INTEGER",
                    is_primary_key=True,
                )
            ],
        )

        metadata_collection = MetadataCollection(
            tables={
                "dataset1.Order-Items": table1,
                "dataset2.order_items": table2,
            }
        )

        with pytest.raises(DuplicateViewNameError) as exc_info:
            generator.generate_complete_lookml_project(metadata_collection)

        error = exc_info.value
        assert error.view_name == "order_items"
        assert len(error.conflicting_tables) == 2
        assert "test-project.dataset1.Order-Items" in str(error)
        assert "test-project.dataset2.order_items" in str(error)
        assert "character_replacements" in str(error)


class TestLookMLFileWriter:
    """Test LookML file writer functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

        self.config = ConcordiaConfig(
            connection=ConnectionConfig(project_id="test-project", datasets=["test"]),
            looker=LookerConfig(
                project_path=self.temp_dir,
                views_path="views/test.view.lkml",
                connection="test-connection",
            ),
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
        with open(file_path) as f:
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
        with open(file_path) as f:
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

        project_dict = {"view": {"test_view": {"dimension": {"id": {"type": "number"}}}}}

        written_files = writer.write_complete_project(project_dict)

        # Verify one file was created
        assert len(written_files) == 1

        for file_path in written_files:
            assert os.path.exists(file_path)
