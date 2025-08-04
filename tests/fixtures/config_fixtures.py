"""
Test fixtures for configuration objects and sample data.
"""

import pytest
from typing import Dict, Any


@pytest.fixture
def sample_model_rules() -> Dict[str, Any]:
    """Sample model rules configuration for testing."""
    return {
        'naming_conventions': {
            'pk_suffix': '_pk',
            'fk_suffix': '_fk'
        },
        'defaults': {
            'measures': ['count'],
            'hide_fields_by_suffix': ['_pk', '_fk']
        },
        'type_mapping': [
            {
                'bq_type': 'STRING',
                'lookml_type': 'dimension',
                'lookml_params': {'type': 'string'}
            },
            {
                'bq_type': 'INTEGER',
                'lookml_type': 'dimension',
                'lookml_params': {'type': 'number'}
            },
            {
                'bq_type': 'TIMESTAMP',
                'lookml_type': 'dimension_group',
                'lookml_params': {
                    'type': 'time',
                    'timeframes': '[raw, time, date, week, month, quarter, year]'
                }
            },
            {
                'bq_type': 'DATE',
                'lookml_type': 'dimension_group',
                'lookml_params': {
                    'type': 'time',
                    'timeframes': '[date, week, month, quarter, year]'
                }
            },
            {
                'bq_type': 'BOOL',
                'lookml_type': 'dimension',
                'lookml_params': {'type': 'yesno'}
            }
        ]
    }


@pytest.fixture
def sample_config(sample_model_rules) -> Dict[str, Any]:
    """Sample complete configuration for testing."""
    return {
        'connection': {
            'project_id': 'test-project',
            'location': 'US',
            'datasets': ['test_dataset']
        },
        'looker': {
            'project_path': './test_looker_project/',
            'views_path': 'views/test_views.view.lkml',
            'connection': 'test-bigquery-connection'
        },
        'model_rules': sample_model_rules
    }


@pytest.fixture
def sample_table_metadata() -> Dict[str, Any]:
    """Sample table metadata for testing."""
    return {
        'table_id': 'users',
        'dataset_id': 'test_dataset',
        'project_id': 'test-project',
        'table_description': 'User information table',
        'columns': [
            {
                'name': 'user_pk',
                'type': 'INTEGER',
                'standardized_type': 'INTEGER',
                'description': 'Primary key for users',
                'is_primary_key': True
            },
            {
                'name': 'email',
                'type': 'STRING',
                'standardized_type': 'STRING',
                'description': 'User email address'
            },
            {
                'name': 'created_at',
                'type': 'TIMESTAMP',
                'standardized_type': 'TIMESTAMP',
                'description': 'Account creation timestamp'
            },
            {
                'name': 'is_active',
                'type': 'BOOL',
                'standardized_type': 'BOOL',
                'description': 'Whether the user is active'
            },
            {
                'name': 'organization_fk',
                'type': 'INTEGER',
                'standardized_type': 'INTEGER',
                'description': 'Foreign key to organization'
            }
        ]
    }


@pytest.fixture
def sample_multiple_tables_metadata(sample_table_metadata) -> Dict[str, Dict[str, Any]]:
    """Sample metadata for multiple tables for testing joins."""
    organizations_metadata = {
        'table_id': 'organizations',
        'dataset_id': 'test_dataset',
        'project_id': 'test-project',
        'table_description': 'Organization information',
        'columns': [
            {
                'name': 'organization_pk',
                'type': 'INTEGER',
                'standardized_type': 'INTEGER',
                'description': 'Primary key for organizations',
                'is_primary_key': True
            },
            {
                'name': 'name',
                'type': 'STRING',
                'standardized_type': 'STRING',
                'description': 'Organization name'
            }
        ]
    }

    return {
        'test_dataset.users': sample_table_metadata,
        'test_dataset.organizations': organizations_metadata
    }


@pytest.fixture
def sample_column_string() -> Dict[str, Any]:
    """Sample string column for testing."""
    return {
        'name': 'email',
        'type': 'STRING',
        'standardized_type': 'STRING',
        'description': 'User email address'
    }


@pytest.fixture
def sample_column_timestamp() -> Dict[str, Any]:
    """Sample timestamp column for testing."""
    return {
        'name': 'created_at',
        'type': 'TIMESTAMP',
        'standardized_type': 'TIMESTAMP',
        'description': 'Account creation timestamp'
    }


@pytest.fixture
def sample_column_primary_key() -> Dict[str, Any]:
    """Sample primary key column for testing."""
    return {
        'name': 'user_pk',
        'type': 'INTEGER',
        'standardized_type': 'INTEGER',
        'description': 'Primary key for users',
        'is_primary_key': True
    }
