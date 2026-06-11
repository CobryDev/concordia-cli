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

Concordia operates on a simple, unidirectional data flow. It reads the metadata (column names, data types, descriptions) directly from your BigQuery tables and views and uses that information to generate clean, consistent, and documented LookML view files.

`Dataform/BigQuery (Source of Truth) -> Concordia -> Looker .view Files`

This ensures that your semantic layer in Looker is a perfect reflection of your transformation layer in the data warehouse, eliminating drift and manual effort.

## Key Features

Automated View Generation: Create a complete, well-structured LookML view from a BigQuery table or view with a single command.

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
# concordia.yaml - Example Configuration

connection:
  # (Recommended) Dataform credentials file; falls back to Google ADC if missing
  dataform_credentials_file: "./.df-credentials.json"
  project_id: "my-gcp-project"
  location: "europe-west2"
  datasets:
    - "marts"
    - "finance"
  # Optional: include BigQuery views in addition to base tables
  include_table_types: ["BASE TABLE", "VIEW"]

looker:
  project_path: "./looker_project/" # Path to your local Looker git repo
  views_path: "views/base/base.view.lkml" # Path for generated base view
  connection: "bigquery-prod" # Looker connection name

model_rules:
  naming_conventions:
    pk_suffix: "_pk"
    fk_suffix: "_fk"
    # Optional: translate unsupported characters so generated names stay LookML-safe
    character_replacements:
      ":": "_" # only letters/numbers/underscores are allowed after replacement

  defaults:
    measures: [count]
    hide_fields_by_suffix: ["_pk", "_fk"]

  type_mapping:
    - bq_type: "TIMESTAMP"
      lookml_type: "dimension_group"
      lookml_params:
        { type: "time", timeframes: "[raw, time, date, week, month]" }
    - bq_type: "INTEGER"
      lookml_type: "dimension"
      lookml_params: { type: "number" }
    # ... and so on
```

### Validation rules that matter

- View and field names must be limited to letters, numbers, and underscores. If your warehouse names contain other characters, add a `character_replacements` mapping (e.g., `":"` -> `"_"`) under `model_rules.naming_conventions`; otherwise generation fails fast with a clear error.
- Generated LookML is parsed with the `lkml` library when available (see [lkml.load examples](https://lkml.readthedocs.io/en/latest/simple.html)) to catch malformed output early. If the installed version cannot parse, a warning is emitted and generation continues.

## Usage

//TODO
