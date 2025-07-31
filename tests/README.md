# Concordia CLI Testing Framework

This directory contains a comprehensive testing suite for the Concordia CLI tool using pytest. The testing framework is designed to ensure reliability and maintain code quality through automated testing.

## Test Structure

```
tests/
├── README.md                          # This file
├── __init__.py                        # Test package init
├── fixtures/                          # Test fixtures and sample data
│   ├── __init__.py
│   └── config_fixtures.py            # Reusable test fixtures
├── unit/                              # Unit tests
│   ├── __init__.py
│   ├── test_field_utils.py           # Tests for field identification logic
│   ├── test_lookml_module.py          # Tests for view generation
│   ├── test_lookml_measure_module.py  # Tests for measure generation
│   ├── test_lookml_explore_module.py  # Tests for explore generation
│   └── test_config.py                 # Tests for YAML configuration
└── integration/                       # Integration tests
    ├── __init__.py
    ├── test_init_command.py           # Tests for init command
    └── test_generate_command.py       # Tests for generate command
```

## Test Categories

### Unit Tests

Unit tests focus on testing individual functions and classes in isolation:

- **`test_field_utils.py`**: Tests the `FieldIdentifier` class for naming conventions, field type identification, and suffix-based logic
- **`test_lookml_module.py`**: Tests view generation, dimension creation, type mapping, and view structure logic
- **`test_lookml_measure_module.py`**: Tests automatic measure generation, numeric measures, amount measures, and custom measures
- **`test_lookml_explore_module.py`**: Tests explore generation, join logic, relationship detection, and custom explore creation
- **`test_config.py`**: Tests YAML configuration generation with comments and proper structure

### Integration Tests

Integration tests verify end-to-end functionality and CLI commands:

- **`test_init_command.py`**: Tests the `init` command including file creation, project detection, error handling, and various edge cases
- **`test_generate_command.py`**: Tests the `generate` command with mocked BigQuery, file I/O operations, and complete workflow validation

## Running Tests

### Prerequisites

Install testing dependencies:

```bash
pip install -r requirements.txt
```

### Run All Tests

```bash
pytest
```

### Run Specific Test Categories

```bash
# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/

# Run specific test file
pytest tests/unit/test_field_utils.py

# Run specific test class or method
pytest tests/unit/test_field_utils.py::TestFieldIdentifier
pytest tests/unit/test_field_utils.py::TestFieldIdentifier::test_is_primary_key_with_default_suffix
```

### Run Tests with Coverage

```bash
# Generate coverage report
pytest --cov=actions --cov-report=html

# View coverage in browser
open htmlcov/index.html
```

### Run Tests with Markers

```bash
# Run only unit tests (if marked)
pytest -m unit

# Run only integration tests (if marked)
pytest -m integration

# Skip slow tests
pytest -m "not slow"
```

## Test Configuration

The testing framework is configured via `pytest.ini` in the project root:

- **Coverage**: Minimum 80% coverage requirement
- **Output**: Verbose output with detailed failure information
- **Reports**: HTML coverage reports generated in `htmlcov/`
- **Markers**: Support for test categorization

## Key Testing Patterns

### Fixtures

Test fixtures provide reusable test data and configurations:

```python
# Using fixtures in tests
def test_field_identification(sample_config, sample_table_metadata):
    generator = LookMLViewGenerator(sample_config)
    result = generator.generate_view_dict(sample_table_metadata)
    assert 'view' in result
```

### Mocking

Integration tests use mocking to isolate external dependencies:

```python
@patch('actions.looker.generate.BigQueryClient')
def test_generate_command(mock_bq_client):
    mock_bq_client.return_value.test_connection.return_value = True
    # Test implementation
```

### Parameterized Tests

Some tests use parameterization for comprehensive coverage:

```python
@pytest.mark.parametrize("field_name,expected", [
    ("user_pk", True),
    ("email", False),
    ("organization_fk", False)
])
def test_is_primary_key(field_name, expected):
    # Test implementation
```

## Test Data

### Sample Configurations

Test fixtures provide realistic sample data:

- Sample model rules with naming conventions
- Sample table metadata with various column types
- Sample BigQuery responses and error conditions

### Temporary File Handling

Integration tests use temporary directories for file operations:

```python
def setup_method(self):
    self.test_dir = tempfile.mkdtemp()
    os.chdir(self.test_dir)

def teardown_method(self):
    os.chdir(self.original_cwd)
    shutil.rmtree(self.test_dir)
```

## Coverage Goals

The testing framework aims for:

- **Overall Coverage**: ≥80% line coverage
- **Unit Test Coverage**: ≥90% for pure logic functions
- **Integration Coverage**: All CLI commands and file operations
- **Error Handling**: All error paths and edge cases

## Best Practices

### Writing Tests

1. **Test Names**: Use descriptive names that explain what is being tested
2. **Arrange-Act-Assert**: Structure tests with clear setup, execution, and verification
3. **Single Responsibility**: Each test should verify one specific behavior
4. **Independent Tests**: Tests should not depend on each other
5. **Realistic Data**: Use realistic test data that matches production scenarios

### Mock Usage

1. **External Dependencies**: Mock BigQuery, file systems, and network calls
2. **Preserve Interfaces**: Ensure mocks match the actual interface contracts
3. **Verify Interactions**: Test that mocked dependencies are called correctly

### Error Testing

1. **Expected Errors**: Test error conditions and exception handling
2. **Edge Cases**: Test boundary conditions and unusual inputs
3. **Recovery**: Test graceful degradation and error recovery

## Continuous Integration

This testing framework is designed to integrate with CI/CD pipelines:

```bash
# CI test command
pytest --cov=actions --cov-report=xml --cov-fail-under=80
```

## Debugging Tests

### Verbose Output

```bash
pytest -v -s tests/unit/test_field_utils.py
```

### Debug Specific Test

```bash
pytest --pdb tests/unit/test_field_utils.py::TestFieldIdentifier::test_is_primary_key_with_default_suffix
```

### Capture Output

```bash
pytest -s  # Don't capture stdout/stderr
```

## Contributing

When adding new functionality:

1. **Add Unit Tests**: Create unit tests for new functions and classes
2. **Add Integration Tests**: Test new CLI commands and workflows
3. **Update Fixtures**: Add new test data as needed
4. **Maintain Coverage**: Ensure coverage requirements are met
5. **Document Tests**: Add docstrings and comments for complex test logic

## Performance

The test suite is designed for reasonable execution time:

- **Unit Tests**: Fast execution (< 1 second each)
- **Integration Tests**: Moderate execution (< 10 seconds each)
- **Full Suite**: Complete in under 2 minutes
- **Parallel Execution**: Supports pytest-xdist for parallel test execution
