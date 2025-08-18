"""
Test fixtures for configuration objects and sample data.
"""

import pytest

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
from actions.models.metadata import ColumnMetadata, TableMetadata


@pytest.fixture
def sample_model_rules() -> ModelRules:
    """Sample model rules configuration for testing."""
    return ModelRules(
        naming_conventions=NamingConventions(pk_suffix="_pk", fk_suffix="_fk"),
        defaults=DefaultBehaviors(measures=["count"], hide_fields_by_suffix=["_pk", "_fk"]),
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
            TypeMapping(
                bq_type="TIMESTAMP",
                lookml_type="dimension_group",
                lookml_params=LookMLParams(
                    type="time",
                    timeframes="[raw, time, date, week, month, quarter, year]",
                ),
            ),
            TypeMapping(
                bq_type="DATE",
                lookml_type="dimension_group",
                lookml_params=LookMLParams(type="time", timeframes="[date, week, month, quarter, year]"),
            ),
            TypeMapping(
                bq_type="BOOL",
                lookml_type="dimension",
                lookml_params=LookMLParams(type="yesno"),
            ),
        ],
    )


@pytest.fixture
def sample_config(sample_model_rules) -> ConcordiaConfig:
    """Sample complete configuration for testing."""
    return ConcordiaConfig(
        connection=ConnectionConfig(project_id="test-project", location="US", datasets=["test_dataset"]),
        looker=LookerConfig(
            project_path="./test_looker_project/",
            views_path="views/test_views.view.lkml",
            connection="test-bigquery-connection",
        ),
        model_rules=sample_model_rules,
    )


@pytest.fixture
def sample_table_metadata() -> TableMetadata:
    """Sample table metadata for testing."""
    return TableMetadata(
        table_id="users",
        dataset_id="test_dataset",
        project_id="test-project",
        table_description="User information table",
        columns=[
            ColumnMetadata(
                name="user_pk",
                type="INTEGER",
                standardized_type="INTEGER",
                description="Primary key for users",
                is_primary_key=True,
            ),
            ColumnMetadata(
                name="email",
                type="STRING",
                standardized_type="STRING",
                description="User email address",
            ),
            ColumnMetadata(
                name="created_at",
                type="TIMESTAMP",
                standardized_type="TIMESTAMP",
                description="Account creation timestamp",
            ),
            ColumnMetadata(
                name="is_active",
                type="BOOL",
                standardized_type="BOOL",
                description="Whether the user is active",
            ),
            ColumnMetadata(
                name="organization_fk",
                type="INTEGER",
                standardized_type="INTEGER",
                description="Foreign key to organization",
            ),
        ],
    )


@pytest.fixture
def sample_multiple_tables_metadata(sample_table_metadata) -> dict[str, TableMetadata]:
    """Sample metadata for multiple tables for testing joins."""
    organizations_metadata = TableMetadata(
        table_id="organizations",
        dataset_id="test_dataset",
        project_id="test-project",
        table_description="Organization information",
        columns=[
            ColumnMetadata(
                name="organization_pk",
                type="INTEGER",
                standardized_type="INTEGER",
                description="Primary key for organizations",
                is_primary_key=True,
            ),
            ColumnMetadata(
                name="name",
                type="STRING",
                standardized_type="STRING",
                description="Organization name",
            ),
        ],
    )

    return {
        "test_dataset.users": sample_table_metadata,
        "test_dataset.organizations": organizations_metadata,
    }


@pytest.fixture
def sample_column_string() -> ColumnMetadata:
    """Sample string column for testing."""
    return ColumnMetadata(
        name="email",
        type="STRING",
        standardized_type="STRING",
        description="User email address",
    )


@pytest.fixture
def sample_column_timestamp() -> ColumnMetadata:
    """Sample timestamp column for testing."""
    return ColumnMetadata(
        name="created_at",
        type="TIMESTAMP",
        standardized_type="TIMESTAMP",
        description="Account creation timestamp",
    )


@pytest.fixture
def sample_column_primary_key() -> ColumnMetadata:
    """Sample primary key column for testing."""
    return ColumnMetadata(
        name="user_pk",
        type="INTEGER",
        standardized_type="INTEGER",
        description="Primary key for users",
        is_primary_key=True,
    )
