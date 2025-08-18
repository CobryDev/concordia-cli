# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Concordia is a Python CLI tool that generates LookML views for Looker from BigQuery table metadata. It maintains BigQuery as the single source of truth and automatically syncs table schemas, column types, and documentation to Looker views.

## Development Commands

### Installation & Setup
```bash
pip install -e .                    # Install in development mode
pip install -r requirements-dev.txt # Install development dependencies
```

### Code Quality & Testing
```bash
# Using nox for automated testing (recommended)
nox -s test                         # Run all tests across Python versions
nox -s unit                         # Run unit tests only
nox -s integration                  # Run integration tests only
nox -s coverage                     # Run tests with coverage requirements
nox -s ci                           # Run CI checks (format, lint, type, coverage)
nox -s all                          # Run comprehensive test suite
nox -s fast                         # Quick test run with minimal output
nox --list                          # See all available sessions

# Individual tool commands (if needed)
ruff check .                        # Lint code (replaces flake8, isort, bandit security checks)
ruff format .                       # Format code (replaces black)
ruff check . --fix                  # Auto-fix linting issues
mypy actions/                       # Type checking
safety check                       # Check dependencies for security issues

# Legacy command (deprecated, use nox instead)
# python run_tests.py [command]     # Old test runner - will be removed
```

### Running the CLI
```bash
python main.py init --force         # Initialize configuration
python main.py looker generate      # Generate LookML from BigQuery
python main.py help                 # Show help
```

## Architecture Overview

### Core Components

**Entry Point**: `main.py` - Click-based CLI with command groups for `init`, `looker`, and `help`

**Actions Package Structure**:
- `actions/init/` - Project initialization and configuration setup
- `actions/looker/` - LookML generation from BigQuery metadata  
- `actions/models/` - Pydantic data models for configuration and metadata
- `actions/utils/` - Shared utilities like safe printing

### Data Flow
1. **Configuration Loading**: Loads `concordia.yaml` with BigQuery connection details and Looker project paths
2. **BigQuery Connection**: Authenticates via Dataform credentials or Google ADC, queries INFORMATION_SCHEMA
3. **Metadata Extraction**: Pulls table schemas, column types, and descriptions from BigQuery
4. **LookML Generation**: Converts metadata to LookML views using configurable type mappings
5. **File Output**: Writes generated LookML views to specified Looker project paths

### Key Models
- `ConcordiaConfig` - Complete configuration structure with connection, Looker, and generation rules
- `MetadataCollection` - Container for BigQuery table metadata  
- `LookMLProject/View/Field` - Object models representing LookML structure
- `BigQueryClient` - Handles authentication and metadata queries

### Configuration System
Uses Pydantic models in `actions/models/config.py` for type-safe YAML configuration. The config supports:
- BigQuery connection via Dataform credentials or Google ADC
- Flexible type mappings from BigQuery to LookML types
- Naming conventions for primary/foreign keys
- Customizable view generation rules

## Testing Approach

- **Unit Tests**: Test individual components in isolation (`tests/unit/`)
- **Integration Tests**: Test full command workflows (`tests/integration/`)  
- **Fixtures**: Shared test data in `tests/fixtures/`
- **Coverage**: Maintains 70% minimum coverage on `actions/` package

## Code Style

- **Line Length**: 100 characters (configured in pyproject.toml)
- **Formatting & Linting**: Uses Ruff for code formatting, import sorting, and linting (replaces black, isort, flake8)
- **Type Hints**: Uses Pydantic models and type hints throughout
- **Error Handling**: Custom `ConfigurationError` for config issues, comprehensive error tracking