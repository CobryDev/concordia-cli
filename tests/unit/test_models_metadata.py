"""
Unit tests for Pydantic models in actions/models/metadata.py.

Tests helper methods, validators, and type checking logic for metadata models
that represent BigQuery table and column information.
"""

import pytest
from pydantic import ValidationError

from actions.models.metadata import ColumnMetadata, MetadataCollection, TableMetadata


class TestColumnMetadata:
    """Test ColumnMetadata model validators and helper methods."""

    def test_valid_column_metadata(self):
        """Test creation with valid column metadata."""
        column = ColumnMetadata(
            name="user_id",
            type="INTEGER",
            standardized_type="INTEGER",
            description="Unique user identifier",
            is_primary_key=True,
            is_foreign_key=False,
            is_nullable=False,
            ordinal_position=1,
        )

        assert column.name == "user_id"
        assert column.type == "INTEGER"
        assert column.standardized_type == "INTEGER"
        assert column.description == "Unique user identifier"
        assert column.is_primary_key is True
        assert column.is_foreign_key is False
        assert column.is_nullable is False
        assert column.ordinal_position == 1

    def test_column_metadata_defaults(self):
        """Test default values for optional fields."""
        column = ColumnMetadata(
            name="test_column",
            type="STRING",
            standardized_type="STRING",
        )

        assert column.description is None
        assert column.is_primary_key is False
        assert column.is_foreign_key is False
        assert column.is_nullable is True
        assert column.ordinal_position is None

    def test_name_validator_empty_string(self):
        """Test name validator rejects empty strings."""
        with pytest.raises(ValidationError) as exc_info:
            ColumnMetadata(
                name="",
                type="STRING",
                standardized_type="STRING",
            )
        assert "Column name cannot be empty" in str(exc_info.value)

    def test_name_validator_whitespace_only(self):
        """Test name validator rejects whitespace-only strings."""
        with pytest.raises(ValidationError) as exc_info:
            ColumnMetadata(
                name="   ",
                type="STRING",
                standardized_type="STRING",
            )
        assert "Column name cannot be empty" in str(exc_info.value)

    def test_name_validator_strips_whitespace(self):
        """Test name validator strips leading/trailing whitespace."""
        column = ColumnMetadata(
            name="  test_column  ",
            type="STRING",
            standardized_type="STRING",
        )
        assert column.name == "test_column"

    def test_type_validator_uppercase_conversion(self):
        """Test type validators convert to uppercase."""
        column = ColumnMetadata(
            name="test_column",
            type="string",
            standardized_type="string",
        )
        assert column.type == "STRING"
        assert column.standardized_type == "STRING"

    def test_is_time_type_true_cases(self):
        """Test is_time_type returns True for time-based types."""
        time_types = ["TIMESTAMP", "DATETIME", "DATE", "TIME"]

        for time_type in time_types:
            column = ColumnMetadata(
                name="test_column",
                type=time_type,
                standardized_type=time_type,
            )
            assert column.is_time_type() is True, f"Failed for type: {time_type}"

    def test_is_time_type_false_cases(self):
        """Test is_time_type returns False for non-time types."""
        non_time_types = ["STRING", "INTEGER", "FLOAT64", "BOOL", "NUMERIC"]

        for non_time_type in non_time_types:
            column = ColumnMetadata(
                name="test_column",
                type=non_time_type,
                standardized_type=non_time_type,
            )
            assert column.is_time_type() is False, f"Failed for type: {non_time_type}"

    def test_is_numeric_type_true_cases(self):
        """Test is_numeric_type returns True for numeric types."""
        numeric_types = ["INTEGER", "INT64", "FLOAT64", "NUMERIC", "DECIMAL", "BIGNUMERIC"]

        for numeric_type in numeric_types:
            column = ColumnMetadata(
                name="test_column",
                type=numeric_type,
                standardized_type=numeric_type,
            )
            assert column.is_numeric_type() is True, f"Failed for type: {numeric_type}"

    def test_is_numeric_type_false_cases(self):
        """Test is_numeric_type returns False for non-numeric types."""
        non_numeric_types = ["STRING", "TIMESTAMP", "DATE", "BOOL", "BYTES"]

        for non_numeric_type in non_numeric_types:
            column = ColumnMetadata(
                name="test_column",
                type=non_numeric_type,
                standardized_type=non_numeric_type,
            )
            assert column.is_numeric_type() is False, f"Failed for type: {non_numeric_type}"

    def test_is_string_type_true_cases(self):
        """Test is_string_type returns True for string types."""
        string_types = ["STRING", "TEXT"]

        for string_type in string_types:
            column = ColumnMetadata(
                name="test_column",
                type=string_type,
                standardized_type=string_type,
            )
            assert column.is_string_type() is True, f"Failed for type: {string_type}"

    def test_is_string_type_false_cases(self):
        """Test is_string_type returns False for non-string types."""
        non_string_types = ["INTEGER", "FLOAT64", "TIMESTAMP", "DATE", "BOOL"]

        for non_string_type in non_string_types:
            column = ColumnMetadata(
                name="test_column",
                type=non_string_type,
                standardized_type=non_string_type,
            )
            assert column.is_string_type() is False, f"Failed for type: {non_string_type}"

    def test_is_boolean_type_true_case(self):
        """Test is_boolean_type returns True for BOOL type."""
        column = ColumnMetadata(
            name="test_column",
            type="BOOL",
            standardized_type="BOOL",
        )
        assert column.is_boolean_type() is True

    def test_is_boolean_type_false_cases(self):
        """Test is_boolean_type returns False for non-boolean types."""
        non_boolean_types = ["STRING", "INTEGER", "FLOAT64", "TIMESTAMP", "DATE"]

        for non_boolean_type in non_boolean_types:
            column = ColumnMetadata(
                name="test_column",
                type=non_boolean_type,
                standardized_type=non_boolean_type,
            )
            assert column.is_boolean_type() is False, f"Failed for type: {non_boolean_type}"


class TestTableMetadata:
    """Test TableMetadata model validators and helper methods."""

    def create_sample_columns(self) -> list[ColumnMetadata]:
        """Helper to create sample columns for testing."""
        return [
            ColumnMetadata(
                name="id",
                type="INTEGER",
                standardized_type="INTEGER",
                is_primary_key=True,
                ordinal_position=1,
            ),
            ColumnMetadata(
                name="user_id",
                type="INTEGER",
                standardized_type="INTEGER",
                is_foreign_key=True,
                ordinal_position=2,
            ),
            ColumnMetadata(
                name="name",
                type="STRING",
                standardized_type="STRING",
                ordinal_position=3,
            ),
            ColumnMetadata(
                name="created_at",
                type="TIMESTAMP",
                standardized_type="TIMESTAMP",
                ordinal_position=4,
            ),
            ColumnMetadata(
                name="is_active",
                type="BOOL",
                standardized_type="BOOL",
                ordinal_position=5,
            ),
        ]

    def test_valid_table_metadata(self):
        """Test creation with valid table metadata."""
        columns = self.create_sample_columns()
        table = TableMetadata(
            table_id="users",
            dataset_id="analytics",
            project_id="my-project",
            table_description="User information table",
            table_type="BASE TABLE",
            columns=columns,
            creation_ddl="CREATE TABLE ...",
        )

        assert table.table_id == "users"
        assert table.dataset_id == "analytics"
        assert table.project_id == "my-project"
        assert table.table_description == "User information table"
        assert table.table_type == "BASE TABLE"
        assert len(table.columns) == 5
        assert table.creation_ddl == "CREATE TABLE ..."

    def test_table_metadata_defaults(self):
        """Test default values for optional fields."""
        columns = self.create_sample_columns()
        table = TableMetadata(
            table_id="users",
            dataset_id="analytics",
            project_id="my-project",
            columns=columns,
        )

        assert table.table_description is None
        assert table.table_type == "BASE TABLE"
        assert table.creation_ddl is None

    def test_identifier_validators_empty_strings(self):
        """Test identifier validators reject empty strings."""
        columns = self.create_sample_columns()

        # Test empty table_id
        with pytest.raises(ValidationError) as exc_info:
            TableMetadata(
                table_id="",
                dataset_id="analytics",
                project_id="my-project",
                columns=columns,
            )
        assert "Identifier cannot be empty" in str(exc_info.value)

        # Test empty dataset_id
        with pytest.raises(ValidationError) as exc_info:
            TableMetadata(
                table_id="users",
                dataset_id="",
                project_id="my-project",
                columns=columns,
            )
        assert "Identifier cannot be empty" in str(exc_info.value)

        # Test empty project_id
        with pytest.raises(ValidationError) as exc_info:
            TableMetadata(
                table_id="users",
                dataset_id="analytics",
                project_id="",
                columns=columns,
            )
        assert "Identifier cannot be empty" in str(exc_info.value)

    def test_identifier_validators_whitespace_only(self):
        """Test identifier validators reject whitespace-only strings."""
        columns = self.create_sample_columns()

        with pytest.raises(ValidationError) as exc_info:
            TableMetadata(
                table_id="   ",
                dataset_id="analytics",
                project_id="my-project",
                columns=columns,
            )
        assert "Identifier cannot be empty" in str(exc_info.value)

    def test_identifier_validators_strip_whitespace(self):
        """Test identifier validators strip leading/trailing whitespace."""
        columns = self.create_sample_columns()
        table = TableMetadata(
            table_id="  users  ",
            dataset_id="  analytics  ",
            project_id="  my-project  ",
            columns=columns,
        )

        assert table.table_id == "users"
        assert table.dataset_id == "analytics"
        assert table.project_id == "my-project"

    def test_full_table_name_property(self):
        """Test full_table_name property returns correct format."""
        columns = self.create_sample_columns()
        table = TableMetadata(
            table_id="users",
            dataset_id="analytics",
            project_id="my-project",
            columns=columns,
        )

        assert table.full_table_name == "my-project.analytics.users"

    def test_table_key_property(self):
        """Test table_key property returns correct format."""
        columns = self.create_sample_columns()
        table = TableMetadata(
            table_id="users",
            dataset_id="analytics",
            project_id="my-project",
            columns=columns,
        )

        assert table.table_key == "analytics.users"

    def test_get_primary_key_columns(self):
        """Test get_primary_key_columns returns only primary key columns."""
        columns = self.create_sample_columns()
        table = TableMetadata(
            table_id="users",
            dataset_id="analytics",
            project_id="my-project",
            columns=columns,
        )

        pk_columns = table.get_primary_key_columns()
        assert len(pk_columns) == 1
        assert pk_columns[0].name == "id"
        assert pk_columns[0].is_primary_key is True

    def test_get_foreign_key_columns(self):
        """Test get_foreign_key_columns returns only foreign key columns."""
        columns = self.create_sample_columns()
        table = TableMetadata(
            table_id="users",
            dataset_id="analytics",
            project_id="my-project",
            columns=columns,
        )

        fk_columns = table.get_foreign_key_columns()
        assert len(fk_columns) == 1
        assert fk_columns[0].name == "user_id"
        assert fk_columns[0].is_foreign_key is True

    def test_get_columns_by_type(self):
        """Test get_columns_by_type returns columns of specified type."""
        columns = self.create_sample_columns()
        table = TableMetadata(
            table_id="users",
            dataset_id="analytics",
            project_id="my-project",
            columns=columns,
        )

        # Test INTEGER columns
        integer_columns = table.get_columns_by_type("INTEGER")
        assert len(integer_columns) == 2
        integer_names = [col.name for col in integer_columns]
        assert "id" in integer_names
        assert "user_id" in integer_names

        # Test STRING columns
        string_columns = table.get_columns_by_type("STRING")
        assert len(string_columns) == 1
        assert string_columns[0].name == "name"

        # Test non-existent type
        nonexistent_columns = table.get_columns_by_type("NONEXISTENT")
        assert len(nonexistent_columns) == 0

    def test_get_column_by_name_found(self):
        """Test get_column_by_name returns correct column when found."""
        columns = self.create_sample_columns()
        table = TableMetadata(
            table_id="users",
            dataset_id="analytics",
            project_id="my-project",
            columns=columns,
        )

        column = table.get_column_by_name("name")
        assert column is not None
        assert column.name == "name"
        assert column.standardized_type == "STRING"

    def test_get_column_by_name_not_found(self):
        """Test get_column_by_name returns None when not found."""
        columns = self.create_sample_columns()
        table = TableMetadata(
            table_id="users",
            dataset_id="analytics",
            project_id="my-project",
            columns=columns,
        )

        column = table.get_column_by_name("nonexistent_column")
        assert column is None

    def test_to_dict(self):
        """Test to_dict method returns proper dictionary structure."""
        columns = self.create_sample_columns()
        table = TableMetadata(
            table_id="users",
            dataset_id="analytics",
            project_id="my-project",
            table_description="User table",
            columns=columns,
        )

        table_dict = table.to_dict()

        assert isinstance(table_dict, dict)
        assert table_dict["table_id"] == "users"
        assert table_dict["dataset_id"] == "analytics"
        assert table_dict["project_id"] == "my-project"
        assert table_dict["table_description"] == "User table"
        assert table_dict["table_type"] == "BASE TABLE"
        assert isinstance(table_dict["columns"], list)
        assert len(table_dict["columns"]) == 5

        # Check that columns are converted to dicts
        first_column = table_dict["columns"][0]
        assert isinstance(first_column, dict)
        assert first_column["name"] == "id"

    def test_from_dict_with_column_dicts(self):
        """Test from_dict class method with column dictionaries."""
        column_dicts = [
            {
                "name": "id",
                "type": "INTEGER",
                "standardized_type": "INTEGER",
                "is_primary_key": True,
            },
            {
                "name": "name",
                "type": "STRING",
                "standardized_type": "STRING",
            },
        ]

        table_data = {
            "table_id": "users",
            "dataset_id": "analytics",
            "project_id": "my-project",
            "columns": column_dicts,
        }

        table = TableMetadata.from_dict(table_data)

        assert table.table_id == "users"
        assert len(table.columns) == 2
        assert isinstance(table.columns[0], ColumnMetadata)
        assert table.columns[0].name == "id"
        assert table.columns[0].is_primary_key is True

    def test_from_dict_with_column_objects(self):
        """Test from_dict class method with ColumnMetadata objects."""
        columns = self.create_sample_columns()

        table_data = {
            "table_id": "users",
            "dataset_id": "analytics",
            "project_id": "my-project",
            "columns": columns,
        }

        table = TableMetadata.from_dict(table_data)

        assert table.table_id == "users"
        assert len(table.columns) == 5
        assert isinstance(table.columns[0], ColumnMetadata)
        assert table.columns[0].name == "id"


class TestMetadataCollection:
    """Test MetadataCollection model and helper methods."""

    def create_sample_tables(self) -> list[TableMetadata]:
        """Helper to create sample tables for testing."""
        columns1 = [
            ColumnMetadata(name="id", type="INTEGER", standardized_type="INTEGER", is_primary_key=True),
            ColumnMetadata(name="name", type="STRING", standardized_type="STRING"),
        ]

        columns2 = [
            ColumnMetadata(name="id", type="INTEGER", standardized_type="INTEGER", is_primary_key=True),
            ColumnMetadata(name="user_id", type="INTEGER", standardized_type="INTEGER", is_foreign_key=True),
            ColumnMetadata(name="amount", type="FLOAT64", standardized_type="FLOAT64"),
        ]

        table1 = TableMetadata(
            table_id="users",
            dataset_id="analytics",
            project_id="my-project",
            columns=columns1,
        )

        table2 = TableMetadata(
            table_id="orders",
            dataset_id="sales",
            project_id="my-project",
            columns=columns2,
        )

        return [table1, table2]

    def test_empty_metadata_collection(self):
        """Test creation of empty metadata collection."""
        collection = MetadataCollection(tables={})

        assert len(collection.tables) == 0
        assert collection.table_count() == 0

    def test_metadata_collection_with_initial_tables(self):
        """Test creation with initial tables dictionary."""
        tables = self.create_sample_tables()
        tables_dict = {table.table_key: table for table in tables}

        collection = MetadataCollection(tables=tables_dict)

        assert len(collection.tables) == 2
        assert collection.table_count() == 2
        assert "analytics.users" in collection.tables
        assert "sales.orders" in collection.tables

    def test_add_table(self):
        """Test add_table method adds table with correct key."""
        collection = MetadataCollection(tables={})
        tables = self.create_sample_tables()

        collection.add_table(tables[0])

        assert collection.table_count() == 1
        assert "analytics.users" in collection.tables
        assert collection.tables["analytics.users"].table_id == "users"

    def test_get_table_found(self):
        """Test get_table returns correct table when found."""
        tables = self.create_sample_tables()
        tables_dict = {table.table_key: table for table in tables}
        collection = MetadataCollection(tables=tables_dict)

        table = collection.get_table("analytics.users")

        assert table is not None
        assert table.table_id == "users"
        assert table.dataset_id == "analytics"

    def test_get_table_not_found(self):
        """Test get_table returns None when table not found."""
        tables = self.create_sample_tables()
        tables_dict = {table.table_key: table for table in tables}
        collection = MetadataCollection(tables=tables_dict)

        table = collection.get_table("nonexistent.table")

        assert table is None

    def test_get_tables_by_dataset(self):
        """Test get_tables_by_dataset returns tables from specific dataset."""
        tables = self.create_sample_tables()

        # Add another table in the same dataset as the first one
        columns3 = [ColumnMetadata(name="id", type="INTEGER", standardized_type="INTEGER")]
        table3 = TableMetadata(
            table_id="profiles",
            dataset_id="analytics",  # Same dataset as users table
            project_id="my-project",
            columns=columns3,
        )
        tables.append(table3)

        tables_dict = {table.table_key: table for table in tables}
        collection = MetadataCollection(tables=tables_dict)

        analytics_tables = collection.get_tables_by_dataset("analytics")

        assert len(analytics_tables) == 2
        table_ids = [table.table_id for table in analytics_tables]
        assert "users" in table_ids
        assert "profiles" in table_ids

        sales_tables = collection.get_tables_by_dataset("sales")
        assert len(sales_tables) == 1
        assert sales_tables[0].table_id == "orders"

        nonexistent_tables = collection.get_tables_by_dataset("nonexistent")
        assert len(nonexistent_tables) == 0

    def test_get_all_tables(self):
        """Test get_all_tables returns all tables as a list."""
        tables = self.create_sample_tables()
        tables_dict = {table.table_key: table for table in tables}
        collection = MetadataCollection(tables=tables_dict)

        all_tables = collection.get_all_tables()

        assert len(all_tables) == 2
        assert isinstance(all_tables, list)
        table_ids = [table.table_id for table in all_tables]
        assert "users" in table_ids
        assert "orders" in table_ids

    def test_table_count(self):
        """Test table_count returns correct number of tables."""
        collection = MetadataCollection(tables={})
        assert collection.table_count() == 0

        tables = self.create_sample_tables()
        for table in tables:
            collection.add_table(table)

        assert collection.table_count() == 2

    def test_to_dict(self):
        """Test to_dict method returns proper dictionary structure."""
        tables = self.create_sample_tables()
        tables_dict = {table.table_key: table for table in tables}
        collection = MetadataCollection(tables=tables_dict)

        collection_dict = collection.to_dict()

        assert isinstance(collection_dict, dict)
        assert len(collection_dict) == 2
        assert "analytics.users" in collection_dict
        assert "sales.orders" in collection_dict

        # Check that each entry is a dict (not a TableMetadata object)
        users_dict = collection_dict["analytics.users"]
        assert isinstance(users_dict, dict)
        assert users_dict["table_id"] == "users"
        assert users_dict["dataset_id"] == "analytics"

    def test_from_dict(self):
        """Test from_dict class method creates proper collection."""
        tables = self.create_sample_tables()
        tables_dict = {table.table_key: table for table in tables}
        collection = MetadataCollection(tables=tables_dict)

        # Convert to dict and back
        collection_dict = collection.to_dict()
        recreated_collection = MetadataCollection.from_dict(collection_dict)

        assert recreated_collection.table_count() == 2
        assert "analytics.users" in recreated_collection.tables
        assert "sales.orders" in recreated_collection.tables

        # Check that objects are properly recreated
        users_table = recreated_collection.get_table("analytics.users")
        assert isinstance(users_table, TableMetadata)
        assert users_table.table_id == "users"
        assert len(users_table.columns) == 2
        assert isinstance(users_table.columns[0], ColumnMetadata)
