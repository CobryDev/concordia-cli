# Contributing to Concordia CLI

Thank you for your interest in contributing to Concordia CLI! This document provides guidelines and information for contributors.

## Development Setup

### Prerequisites

- Python 3.9 or higher
- Git

### Setup Instructions

1. **Fork and clone the repository**

   ```bash
   git clone https://github.com/your-username/concordia-cli.git
   cd concordia-cli
   ```

2. **Create a virtual environment**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Verify setup**
   ```bash
   python run_tests.py
   ```

## Testing Framework

### Running Tests

Our comprehensive testing framework includes 154+ automated tests:

```bash
# Run all tests
python run_tests.py

# Run specific test categories
python run_tests.py unit          # Unit tests only
python run_tests.py integration   # Integration tests only
python run_tests.py coverage      # Tests with coverage report
python run_tests.py fast          # Quick test run

# Run specific test files
python run_tests.py --test tests/unit/test_field_utils.py
pytest tests/unit/test_lookml_module.py::TestLookMLViewGenerator -v
```

### Writing Tests

#### Unit Tests

- **Location**: `tests/unit/`
- **Purpose**: Test individual functions and classes in isolation
- **Naming**: `test_<module_name>.py`
- **Pattern**: Use pytest fixtures from `tests/fixtures/config_fixtures.py`

Example:

```python
def test_field_identification(sample_config):
    identifier = FieldIdentifier(sample_config['model_rules'])
    assert identifier.is_primary_key('user_pk') is True
    assert identifier.is_foreign_key('organization_fk') is True
```

#### Integration Tests

- **Location**: `tests/integration/`
- **Purpose**: Test CLI commands and end-to-end workflows
- **Requirements**: Use temporary directories and mock external dependencies

Example:

```python
@patch('actions.looker.generate.BigQueryClient')
def test_generate_command(mock_bq_client):
    mock_bq_client.return_value.test_connection.return_value = True
    result = self.runner.invoke(cli, ['looker', 'generate'])
    assert result.exit_code == 0
```

### Test Requirements

1. **Coverage**: Maintain ≥80% code coverage
2. **Independence**: Tests must not depend on each other
3. **Isolation**: Mock external dependencies (BigQuery, file system)
4. **Descriptive Names**: Use clear, descriptive test method names
5. **Documentation**: Add docstrings explaining what each test validates

## Code Quality Standards

### Code Style

- Follow PEP 8 guidelines
- Use descriptive variable and function names
- Add docstrings to all public functions and classes
- Keep functions focused and single-purpose

### Quality Checks

Our CI pipeline runs several quality checks:

```bash
# Linting
flake8 actions/ tests/ --max-line-length=100

# Type checking (optional but recommended)
mypy actions/ --ignore-missing-imports

# Security scanning
bandit -r actions/
safety check
```

## Contribution Workflow

### 1. Create an Issue

Before starting work, create an issue to discuss:

- Bug reports: Use the bug report template
- Feature requests: Use the feature request template
- Include clear descriptions and use cases

### 2. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-description
```

### 3. Make Changes

- Write clean, well-documented code
- Add tests for new functionality
- Update documentation if needed
- Follow the existing code patterns

### 4. Test Your Changes

```bash
# Run the full test suite
python run_tests.py

# Ensure coverage requirements are met
python run_tests.py coverage

# Run quality checks
flake8 actions/ tests/
```

### 5. Commit Your Changes

Use conventional commit messages:

```bash
git commit -m "feat: add support for custom explore generation"
git commit -m "fix: resolve foreign key detection edge case"
git commit -m "test: add unit tests for field utilities"
git commit -m "docs: update testing documentation"
```

### 6. Submit a Pull Request

- Use the pull request template
- Include a clear description of changes
- Link to related issues
- Ensure all CI checks pass

## CI/CD Pipeline

Our GitHub Actions workflows automatically:

### Test Workflow (`.github/workflows/test.yml`)

- **Triggers**: Push to main/develop, pull requests
- **Matrix**: Multiple OS (Ubuntu, macOS, Windows) and Python versions
- **Steps**: Dependency check, unit tests, integration tests, coverage
- **Artifacts**: Coverage reports uploaded to Codecov

### Quality Workflow (`.github/workflows/quality.yml`)

- **Triggers**: Push and pull requests
- **Checks**: Code formatting, import sorting, linting, type checking, security
- **Reports**: Security and vulnerability reports

### Release Workflow (`.github/workflows/release.yml`)

- **Triggers**: Version tags (v\*)
- **Steps**: Full test suite, release creation with test results

### Documentation Workflow (`.github/workflows/docs.yml`)

- **Triggers**: Documentation file changes
- **Validation**: Documentation consistency and example verification

## Project Structure

```
concordia-cli/
├── actions/                    # Main application code
│   ├── init/                  # Initialization commands
│   ├── looker/                # LookML generation
│   └── help/                  # Help system
├── tests/                     # Comprehensive test suite
│   ├── unit/                  # Unit tests
│   ├── integration/           # Integration tests
│   └── fixtures/              # Test fixtures and sample data
├── .github/                   # GitHub workflows and templates
├── run_tests.py              # Test runner script
├── pytest.ini               # pytest configuration
└── requirements.txt          # Dependencies
```

## Areas for Contribution

### High Priority

1. **Additional BigQuery Data Types**: Support for ARRAY, STRUCT, GEOGRAPHY
2. **Enhanced Join Logic**: More sophisticated relationship detection
3. **Custom LookML Templates**: User-defined view/explore templates
4. **Performance Optimization**: Faster metadata extraction and generation

### Testing Improvements

1. **Performance Tests**: Benchmark test suite for large datasets
2. **Mock Improvements**: More realistic BigQuery response mocking
3. **Edge Case Coverage**: Additional boundary condition testing
4. **Integration Scenarios**: More complex multi-table scenarios

### Documentation

1. **User Guides**: Step-by-step tutorials for common workflows
2. **API Documentation**: Detailed module and function documentation
3. **Best Practices**: LookML generation best practices guide
4. **Troubleshooting**: Common issues and solutions

## Getting Help

- **Issues**: Check existing issues or create a new one
- **Discussions**: Use GitHub Discussions for questions and ideas
- **Documentation**: Refer to `tests/README.md` for testing details
- **Code Examples**: Look at existing tests for patterns and examples

## Recognition

Contributors will be recognized in:

- Release notes for significant contributions
- CONTRIBUTORS.md file (coming soon)
- GitHub contributor graphs and statistics

Thank you for helping make Concordia CLI better! 🚀
