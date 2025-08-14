#!/usr/bin/env python3
"""
Example demonstrating the refactored type-safe approach using Pydantic models.

This script shows how the refactoring eliminates primitive dictionary usage
in favor of structured, validated data models.
"""

from actions.models.config import (
    ConcordiaConfig,
    ConnectionConfig,
    LookerConfig,
    ModelRules,
)
from actions.models.metadata import TableMetadata, ColumnMetadata, MetadataCollection
from actions.models.lookml import (
    LookMLView,
    Dimension,
    DimensionType,
    DimensionGroup,
    DimensionGroupType,
)


def main():
    print("🚀 Concordia CLI - Type-Safe Refactoring Demo")
    print("=" * 50)

    # Example 1: Configuration with type safety
    print("\n1. Creating type-safe configuration (no more Dict[str, Any]):")
    print("-" * 55)

    config = ConcordiaConfig(
        connection=ConnectionConfig(
            project_id="my-project", location="US", datasets=["analytics", "staging"]
        ),
        looker=LookerConfig(
            project_path="./looker_project/",
            views_path="views/generated.view.lkml",
            connection="bigquery_connection",
        ),
        model_rules=ModelRules.from_dict(
            {
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
            }
        ),
    )

    print(f"✅ Configuration created: {config.connection.project_id}")
    print(f"   Datasets: {', '.join(config.connection.datasets)}")
    print(f"   Looker connection: {config.looker.connection}")

    # Example 2: Table metadata with type safety
    print("\n2. Creating type-safe table metadata:")
    print("-" * 40)

    table_metadata = TableMetadata(
        table_id="users",
        dataset_id="analytics",
        project_id="my-project",
        table_description="User information table",
        columns=[
            ColumnMetadata(
                name="user_id",
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
                description="Whether user is active",
            ),
        ],
    )

    print(f"✅ Table metadata created: {table_metadata.full_table_name}")
    print(f"   Columns: {len(table_metadata.columns)}")
    print(f"   Primary keys: {len(table_metadata.get_primary_key_columns())}")

    # Example 3: LookML generation with type safety
    print("\n3. Creating type-safe LookML components:")
    print("-" * 42)

    # Create dimensions
    email_dimension = Dimension(
        name="email",
        type=DimensionType.STRING,
        sql="${TABLE}.email",
        description="User email address",
    )

    created_at_group = DimensionGroup(
        name="created_at",
        type=DimensionGroupType.TIME,
        sql="${TABLE}.created_at",
        description="Account creation timestamp",
        timeframes=["raw", "time", "date", "week", "month", "quarter", "year"],
    )

    # Create LookML view
    lookml_view = LookMLView(
        name="users",
        sql_table_name="`my-project.analytics.users`",
        connection="bigquery_connection",
        description="User information view",
    )

    lookml_view.add_dimension(email_dimension)
    lookml_view.add_dimension_group(created_at_group)

    print(f"✅ LookML view created: {lookml_view.name}")
    print(f"   Dimensions: {len(lookml_view.dimensions)}")
    print(f"   Dimension groups: {len(lookml_view.dimension_groups)}")

    # Example 4: Demonstrate type safety benefits
    print("\n4. Type safety benefits:")
    print("-" * 25)

    print("✅ Autocomplete and IDE support")
    print("✅ Compile-time error detection")
    print("✅ Automatic validation")
    print("✅ Self-documenting code")
    print("✅ Consistent data structures")

    # Example of validation
    try:
        # This would fail validation due to empty name
        invalid_column = ColumnMetadata(
            name="",  # This will fail validation
            type="STRING",
            standardized_type="STRING",
        )
    except Exception as e:
        print(f"✅ Validation caught error: {str(e)[:60]}...")

    # Example 5: Easy serialization
    print("\n5. Easy serialization to/from dictionaries:")
    print("-" * 48)

    # Convert to dict for YAML/JSON output
    config_dict = config.to_dict()
    print(f"✅ Config serialized to dict with {len(config_dict)} top-level keys")

    # Create from dict (e.g., from YAML file)
    config_from_dict = ConcordiaConfig.from_dict(config_dict)
    print(f"✅ Config recreated from dict: {config_from_dict.connection.project_id}")

    print("\n🎉 Type-safe refactoring complete!")
    print("   No more Dict[str, Any] - everything is properly typed!")


if __name__ == "__main__":
    main()
