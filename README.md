Concordia

![concordia-logo](/docs/logo.jpg)

<p align="center">
<em>Bring harmony to your data stack.</em>
</p>

<p align="center">
<a href="#what-is-concordia">What is it?</a> •
<a href="#how-it-works">How it Works</a> •
<a href="#key-features">Features</a> •
<a href="#getting-started">Getting Started</a> •
<a href="#usage">Usage</a> •
<a href="#configuration">Configuration</a>
</p>

What is Concordia?
Concordia is a command-line interface (CLI) tool that automates the creation and maintenance of Looker views, ensuring they are always in sync with your BigQuery data warehouse. It establishes your BigQuery/Dataform schema as the single source of truth and propagates its structure and documentation directly into your Looker project.

If you've ever had to:

- Manually create a new LookML view for every new table in your warehouse.
- Update a LookML dimension because a column name changed in BigQuery.
- Copy and paste column descriptions from a dbt/dataform model into a Looker view.
- Notice that the documentation in Looker is out of date with the real-world table.

...then Concordia is the tool for you.

## How it Works

Concordia operates on a simple, unidirectional data flow. It reads the metadata (column names, data types, descriptions) directly from your BigQuery tables and uses that information to generate clean, consistent, and documented LookML view files.

`Dataform/BigQuery (Source of Truth) -> Concordia -> Looker .view Files`

This ensures that your semantic layer in Looker is a perfect reflection of your transformation layer in the data warehouse, eliminating drift and manual effort.

## Key Features

Automated View Generation: Create a complete, well-structured LookML view from a BigQuery table with a single command.

- Documentation Sync: Automatically pulls column descriptions from BigQuery and populates the description tag in your LookML dimensions.
- Convention over Configuration: Uses smart naming conventions (e.g., for primary and foreign keys) to generate better LookML.
- Intelligent Defaults: Automatically adds a count measure, hides key fields, and creates a set for drill fields.
- Simple Configuration: A single concordia.yml file manages all project settings.
- Secure Authentication: Leverages existing Dataform credentials files or Google Application Default Credentials (ADC) so you don't have to manage new secrets.

## Getting Started

1. Installation
   (Placeholder for installation instructions, e.g., pip install concordia-cli)
2. Initialization
   Navigate to the root of your analytics repository and run: `concordia init`. This will create a concordia.yml file in your project. This is where you will configure the tool.

## Configuration

All configuration is handled in the concordia.yml file.

```yaml
# concordia.yml - Example Configuration

# BigQuery Connection Details
connection:
  # (Recommended) Point to your Dataform credentials file.
  dataform_credentials_file: './.df-credentials.json'

  # If the file above is not found, Concordia falls back to Google ADC.

  # The GCP project ID and location to target.
  project_id: 'my-gcp-project'
  location: 'europe-west2'

  # The datasets to scan for tables.
  datasets:
    - 'marts'
    - 'finance'

# Looker project configuration
looker:
  project_path: './looker_project/' # Path to your local Looker git repo
  views_path: 'views/base/base.view.lkml' # Path for generated base view
  connection: 'bigquery-prod' # The name of your Looker connection

# Rules for how models and fields are generated
model_rules:
  # Define how to identify PKs and FKs from column names
  naming_conventions:
    pk_suffix: '_pk'
    fk_suffix: '_fk'

  # Define default behaviors for generated views
  defaults:
    measures: [count]
    hide_fields_by_suffix: ['_pk', '_fk']

  # Map BigQuery data types to LookML
  type_mapping:
    - bq_type: 'TIMESTAMP'
      lookml_type: 'dimension_group'
      lookml_params: { type: 'time', timeframes: '[raw, time, date, week, month]' }
    - bq_type: 'INTEGER'
      lookml_type: 'dimension'
      lookml_params: { type: 'number' }
    # ... and so on


# BigQuery Connection Details

connection:

# (Recommended) Point to your Dataform credentials file.

dataform_credentials_file: './.df-credentials.json'

# If the file above is not found, Concordia falls back to Google ADC.

# The GCP project ID and location to target.

project_id: 'my-gcp-project'
location: 'europe-west2'

# The datasets to scan for tables.

datasets: - 'marts' - 'finance'

# Looker project configuration

looker:
project_path: './looker_project/' # Path to your local Looker git repo
views_path: 'views/generated_views.view.lkml' # File path where generated views will be written
explores_path: 'views/generated_explores.view.lkml' # File path where generated explores will be written
connection: 'bigquery-prod' # The name of your Looker connection

# Rules for how models and fields are generated

model_rules:

# Define how to identify PKs and FKs from column names

naming_conventions:
pk_suffix: '\_pk'
fk_suffix: '\_fk'

# Define default behaviors for generated views

defaults:
measures: [count]
hide_fields_by_suffix: ['_pk', '_fk']

# Map BigQuery data types to LookML

type_mapping: - bq_type: 'TIMESTAMP'
lookml_type: 'dimension_group'
lookml_params: { type: 'time', timeframes: '[raw, time, date, week, month]' } - bq_type: 'INTEGER'
lookml_type: 'dimension'
lookml_params: { type: 'number' } # ... and so on
```

## Usage

//TODO
