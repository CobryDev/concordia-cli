"""
Configuration documentation generator for Concordia.

This module generates user-friendly documentation about the configuration schema,
including examples and explanations for each field.
"""


def generate_config_docs() -> str:
    """Generate comprehensive configuration documentation.

    Returns:
        Markdown documentation as a string
    """
    docs = []

    # Header
    docs.append("# Concordia Configuration Guide")
    docs.append("")
    docs.append("This guide explains all available configuration options in `concordia.yaml`.")
    docs.append("")

    # Overview
    docs.append("## Overview")
    docs.append("")
    docs.append("Concordia uses a YAML configuration file to define:")
    docs.append("- **BigQuery Connection**: How to connect to your BigQuery instance")
    docs.append("- **Looker Project**: Where to write generated LookML files")
    docs.append("- **Model Rules**: How to convert BigQuery types to LookML")
    docs.append("")

    # Validation
    docs.append("## Configuration Validation")
    docs.append("")
    docs.append("Concordia provides built-in configuration validation:")
    docs.append("")
    docs.append("```bash")
    docs.append("# Validate configuration (lenient mode, allows template values)")
    docs.append("concordia config validate")
    docs.append("")
    docs.append("# Validate configuration (strict mode, for production)")
    docs.append("concordia config validate --strict")
    docs.append("")
    docs.append("# Generate JSON schema")
    docs.append("concordia config validate --schema")
    docs.append("```")
    docs.append("")

    # Full example
    docs.append("## Complete Configuration Example")
    docs.append("")
    docs.append("```yaml")
    docs.append(_generate_example_config())
    docs.append("```")
    docs.append("")

    # Detailed sections
    docs.extend(_generate_connection_docs())
    docs.extend(_generate_looker_docs())
    docs.extend(_generate_model_rules_docs())

    # Troubleshooting
    docs.extend(_generate_troubleshooting_docs())

    return "\n".join(docs)


def _generate_example_config() -> str:
    """Generate a complete example configuration."""
    return '''# BigQuery connection configuration
connection:
  # Path to Dataform credentials (optional, uses ADC if not provided)
  dataform_credentials_file: "./.df-credentials.json"

  # GCP project ID (optional, extracted from credentials if not provided)
  project_id: "my-analytics-project"

  # BigQuery location (optional, defaults to 'US')
  location: "US"

  # List of datasets to scan for tables (required)
  datasets:
    - "raw_data"
    - "staging"
    - "marts"

# Looker project configuration
looker:
  # Path to your Looker project directory
  project_path: "./looker-project"

  # Relative path for the generated views file
  views_path: "views/concordia_generated.view.lkml"

  # Name of your BigQuery connection in Looker
  connection: "bigquery_prod"

# Model generation rules
model_rules:
  # Naming conventions for identifying key columns
  naming_conventions:
    pk_suffix: "_pk"      # Primary key suffix
    fk_suffix: "_fk"      # Foreign key suffix
    view_prefix: ""       # Prefix for view names
    view_suffix: ""       # Suffix for view names

  # Default behaviors for all views
  defaults:
    measures: ["count"]           # Default measures to create
    hide_fields_by_suffix:        # Field suffixes to hide
      - "_pk"
      - "_fk"

  # BigQuery to LookML type mappings
  type_mapping:
    - bq_type: "STRING"
      lookml_type: "dimension"
      lookml_params:
        type: "string"

    - bq_type: "INTEGER"
      lookml_type: "dimension"
      lookml_params:
        type: "number"

    - bq_type: "TIMESTAMP"
      lookml_type: "dimension_group"
      lookml_params:
        type: "time"
        timeframes: "time,date,week,month,quarter,year"
        sql: "${TABLE}.${FIELD}"'''


def _generate_connection_docs() -> list[str]:
    """Generate BigQuery connection documentation."""
    docs = []

    docs.append("## BigQuery Connection Configuration")
    docs.append("")
    docs.append("The `connection` section configures how Concordia connects to BigQuery.")
    docs.append("")

    # dataform_credentials_file
    docs.append("### `dataform_credentials_file` (optional)")
    docs.append("")
    docs.append("Path to your Dataform credentials JSON file.")
    docs.append("")
    docs.append("- **Type**: `string`")
    docs.append("- **Default**: `null` (uses Google Application Default Credentials)")
    docs.append("- **Examples**:")
    docs.append("  ```yaml")
    docs.append('  dataform_credentials_file: "./.df-credentials.json"')
    docs.append('  dataform_credentials_file: "./config/dataform-creds.json"')
    docs.append("  ```")
    docs.append("")
    docs.append("**Validation Rules**:")
    docs.append("- File must exist and be readable")
    docs.append("- Must have `.json` extension")
    docs.append("- Must be a valid JSON file")
    docs.append("")

    # project_id
    docs.append("### `project_id` (optional)")
    docs.append("")
    docs.append("Your Google Cloud Platform project ID.")
    docs.append("")
    docs.append("- **Type**: `string`")
    docs.append("- **Default**: Extracted from credentials")
    docs.append("- **Examples**:")
    docs.append("  ```yaml")
    docs.append('  project_id: "my-analytics-project"')
    docs.append('  project_id: "prod-data-warehouse"')
    docs.append("  ```")
    docs.append("")
    docs.append("**Validation Rules**:")
    docs.append("- Must be 6-30 characters long")
    docs.append("- Can contain letters, numbers, hyphens, and underscores")
    docs.append("- Cannot be template values like 'your-gcp-project-id'")
    docs.append("")

    # location
    docs.append("### `location` (optional)")
    docs.append("")
    docs.append("BigQuery location/region for your datasets.")
    docs.append("")
    docs.append("- **Type**: `string`")
    docs.append('- **Default**: `"US"`')
    docs.append('- **Common Values**: `"US"`, `"EU"`, `"us-central1"`, `"europe-west1"`')
    docs.append("- **Examples**:")
    docs.append("  ```yaml")
    docs.append('  location: "US"          # Multi-regional')
    docs.append('  location: "EU"          # Multi-regional')
    docs.append('  location: "us-central1"  # Regional')
    docs.append("  ```")
    docs.append("")

    # datasets
    docs.append("### `datasets` (required)")
    docs.append("")
    docs.append("List of BigQuery datasets to scan for tables.")
    docs.append("")
    docs.append("- **Type**: `array of strings`")
    docs.append("- **Required**: At least one dataset must be specified")
    docs.append("- **Examples**:")
    docs.append("  ```yaml")
    docs.append("  datasets:")
    docs.append('    - "raw_data"')
    docs.append('    - "staging"')
    docs.append('    - "marts"')
    docs.append("  ```")
    docs.append("")
    docs.append("**Validation Rules**:")
    docs.append("- At least one dataset is required")
    docs.append("- Dataset names cannot be empty")
    docs.append("- Must contain only letters, numbers, and underscores")
    docs.append("")

    return docs


def _generate_looker_docs() -> list[str]:
    """Generate Looker configuration documentation."""
    docs = []

    docs.append("## Looker Project Configuration")
    docs.append("")
    docs.append("The `looker` section configures where to write generated LookML files.")
    docs.append("")

    # project_path
    docs.append("### `project_path` (required)")
    docs.append("")
    docs.append("Path to your Looker project directory.")
    docs.append("")
    docs.append("- **Type**: `string`")
    docs.append("- **Examples**:")
    docs.append("  ```yaml")
    docs.append('  project_path: "./looker-project"')
    docs.append('  project_path: "../my-looker-project"')
    docs.append('  project_path: "/absolute/path/to/looker"')
    docs.append("  ```")
    docs.append("")
    docs.append("**Validation Rules**:")
    docs.append("- Directory must exist")
    docs.append("- Must be a valid directory path")
    docs.append("- Cannot be empty")
    docs.append("")

    # views_path
    docs.append("### `views_path` (required)")
    docs.append("")
    docs.append("Relative path within the Looker project for the generated views file.")
    docs.append("")
    docs.append("- **Type**: `string`")
    docs.append("- **Examples**:")
    docs.append("  ```yaml")
    docs.append('  views_path: "views/concordia_views.view.lkml"')
    docs.append('  views_path: "generated/bigquery_views.view.lkml"')
    docs.append('  views_path: "models/warehouse.view.lkml"')
    docs.append("  ```")
    docs.append("")
    docs.append("**Validation Rules**:")
    docs.append("- Must end with `.view.lkml`")
    docs.append("- Must be a relative path (not absolute)")
    docs.append("- Parent directories will be created if they don't exist")
    docs.append("")

    # connection
    docs.append("### `connection` (required)")
    docs.append("")
    docs.append("Name of your BigQuery connection in Looker.")
    docs.append("")
    docs.append("- **Type**: `string`")
    docs.append("- **Examples**:")
    docs.append("  ```yaml")
    docs.append('  connection: "bigquery_prod"')
    docs.append('  connection: "bq_analytics"')
    docs.append('  connection: "data_warehouse"')
    docs.append("  ```")
    docs.append("")
    docs.append("**Validation Rules**:")
    docs.append("- Cannot be empty")
    docs.append("- Cannot be template values like 'your-bigquery-connection'")
    docs.append("- Can contain letters, numbers, underscores, and hyphens")
    docs.append("")

    return docs


def _generate_model_rules_docs() -> list[str]:
    """Generate model rules documentation."""
    docs = []

    docs.append("## Model Generation Rules")
    docs.append("")
    docs.append("The `model_rules` section controls how BigQuery metadata is converted to LookML.")
    docs.append("")

    # naming_conventions
    docs.append("### Naming Conventions")
    docs.append("")
    docs.append("Configure how Concordia identifies different types of columns.")
    docs.append("")
    docs.append("```yaml")
    docs.append("naming_conventions:")
    docs.append('  pk_suffix: "_pk"      # Primary key suffix')
    docs.append('  fk_suffix: "_fk"      # Foreign key suffix')
    docs.append('  view_prefix: ""       # View name prefix')
    docs.append('  view_suffix: ""       # View name suffix')
    docs.append("```")
    docs.append("")

    # defaults
    docs.append("### Default Behaviors")
    docs.append("")
    docs.append("Configure default measures and field visibility.")
    docs.append("")
    docs.append("```yaml")
    docs.append("defaults:")
    docs.append('  measures: ["count"]           # Measures to create for each view')
    docs.append("  hide_fields_by_suffix:        # Field suffixes to hide in Looker")
    docs.append('    - "_pk"')
    docs.append('    - "_fk"')
    docs.append("```")
    docs.append("")

    # type_mapping
    docs.append("### Type Mapping")
    docs.append("")
    docs.append("Define how BigQuery column types are converted to LookML fields.")
    docs.append("")
    docs.append("```yaml")
    docs.append("type_mapping:")
    docs.append('  - bq_type: "STRING"')
    docs.append('    lookml_type: "dimension"')
    docs.append("    lookml_params:")
    docs.append('      type: "string"')
    docs.append("  ")
    docs.append('  - bq_type: "TIMESTAMP"')
    docs.append('    lookml_type: "dimension_group"')
    docs.append("    lookml_params:")
    docs.append('      type: "time"')
    docs.append('      timeframes: "time,date,week,month,quarter,year"')
    docs.append("```")
    docs.append("")
    docs.append("**Available LookML Types**:")
    docs.append("- `dimension`: Regular dimension fields")
    docs.append("- `dimension_group`: Time-based dimension groups")
    docs.append("- `measure`: Aggregate measures")
    docs.append("")
    docs.append("**Common BigQuery Types**:")
    docs.append("- `STRING`, `INTEGER`, `FLOAT64`, `BOOLEAN`")
    docs.append("- `TIMESTAMP`, `DATETIME`, `DATE`, `TIME`")
    docs.append("- `NUMERIC`, `BIGNUMERIC`")
    docs.append("- `ARRAY`, `STRUCT`, `JSON`")
    docs.append("")

    return docs


def _generate_troubleshooting_docs() -> list[str]:
    """Generate troubleshooting documentation."""
    docs = []

    docs.append("## Troubleshooting")
    docs.append("")

    docs.append("### Common Validation Errors")
    docs.append("")

    docs.append("**Configuration file not found**")
    docs.append("```")
    docs.append("❌ Configuration file not found: concordia.yaml")
    docs.append("```")
    docs.append("- Make sure `concordia.yaml` exists in your current directory")
    docs.append("- Use `--file` flag to specify a different path")
    docs.append("- Run `concordia init` to create a new configuration")
    docs.append("")

    docs.append("**Template values not replaced**")
    docs.append("```")
    docs.append("❌ Please replace template project ID with your actual GCP project ID")
    docs.append("```")
    docs.append("- Update template values like `your-gcp-project-id` with real values")
    docs.append("- Run `concordia config validate` to see all template values")
    docs.append("- Use strict mode (`--strict`) for production validation")
    docs.append("")

    docs.append("**Missing files or directories**")
    docs.append("```")
    docs.append("❌ Looker project directory does not exist: ./looker-project")
    docs.append("```")
    docs.append("- Ensure all paths point to existing files/directories")
    docs.append("- Use absolute paths if relative paths aren't working")
    docs.append("- Create missing directories before running validation")
    docs.append("")

    docs.append("**Invalid type mappings**")
    docs.append("```")
    docs.append("❌ Invalid LookML type 'invalid_type'. Must be one of: dimension, dimension_group, measure")
    docs.append("```")
    docs.append("- Check that all `lookml_type` values are valid")
    docs.append("- Ensure type mappings include required parameters")
    docs.append("- At least one type mapping is required")
    docs.append("")

    docs.append("### Validation Modes")
    docs.append("")
    docs.append("**Lenient Mode (Default)**")
    docs.append("- Allows template values and missing files")
    docs.append("- Good for development and testing")
    docs.append("- Shows warnings for issues that should be fixed")
    docs.append("")
    docs.append("**Strict Mode**")
    docs.append("- Requires all template values to be replaced")
    docs.append("- Requires all files and directories to exist")
    docs.append("- Required for production use")
    docs.append("- Use with `concordia config validate --strict`")
    docs.append("")

    return docs


def save_config_docs(output_path: str = "CONFIG.md") -> None:
    """Save configuration documentation to a file.

    Args:
        output_path: Path to save the documentation file
    """
    docs = generate_config_docs()

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(docs)
