from typing import Optional

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq


def generate_concordia_config(dataform_path: Optional[str], looker_path: Optional[str]) -> CommentedMap:
    """Generate the concordia.yaml configuration with comments using ruamel.yaml."""

    # Create the main configuration object
    config = CommentedMap()

    # Add file header comment
    config.yaml_set_start_comment("concordia.yml - Generated Configuration")

    # Connection section
    connection = CommentedMap()
    connection.yaml_set_comment_before_after_key(
        "dataform_credentials_file",
        before="""Method 1 (Preferred): Point to a Dataform credentials JSON file.
Concordia will parse the 'credentials' key from this file to authenticate.
The path should be relative to this config file.""",
    )

    connection["dataform_credentials_file"] = (
        "./.df-credentials.json" if dataform_path else "path/to/your/.df-credentials.json"
    )

    connection.yaml_set_comment_before_after_key(
        "project_id",
        before="""Method 2 (Fallback): If 'dataform_credentials_file' is omitted or invalid,
Concordia will automatically use Google Application Default Credentials (ADC).
This is useful for local development or running in a configured GCP environment.

The GCP project ID to target. If not provided here, it will be inferred
from the credentials file or ADC.""",
    )
    connection["project_id"] = "your-gcp-project-id"

    connection.yaml_set_comment_before_after_key(
        "location",
        before="""The default location/region for BigQuery jobs. If not provided, it will be
inferred from the credentials file.""",
    )
    connection["location"] = "your-region"  # e.g., 'europe-west2'

    connection.yaml_set_comment_before_after_key("datasets", before="The datasets to scan for tables.")
    datasets = CommentedSeq(["dataset1", "dataset2"])
    connection["datasets"] = datasets

    config["connection"] = connection
    config.yaml_set_comment_before_after_key("connection", before="BigQuery Connection Details")

    # Looker section
    looker = CommentedMap()
    looker["project_path"] = f"./{looker_path}/" if looker_path else "./path/to/your/looker_project/"
    looker["views_path"] = "views/generated_views.view.lkml"
    looker["connection"] = "your-bigquery-connection"

    # Add inline comments for looker section
    looker.yaml_add_eol_comment("File path where generated views will be written", "views_path")
    looker.yaml_add_eol_comment("This is the Looker connection name", "connection")

    config["looker"] = looker
    config.yaml_set_comment_before_after_key("looker", before="Looker project configuration")

    # Model rules section
    model_rules = CommentedMap()

    # Naming conventions
    naming_conventions = CommentedMap()
    naming_conventions["pk_suffix"] = "_pk"
    naming_conventions["fk_suffix"] = "_fk"
    model_rules["naming_conventions"] = naming_conventions
    model_rules.yaml_set_comment_before_after_key(
        "naming_conventions", before="Define how database column names are interpreted"
    )

    # Defaults
    defaults = CommentedMap()
    measures = CommentedSeq(["count"])
    measures.yaml_add_eol_comment("Automatically create a count measure", 0)
    defaults["measures"] = measures

    hide_fields = CommentedSeq(["_pk", "_fk"])
    hide_fields.yaml_add_eol_comment("Hide PKs and FKs", 0)
    defaults["hide_fields_by_suffix"] = hide_fields

    model_rules["defaults"] = defaults
    model_rules.yaml_set_comment_before_after_key("defaults", before="Define default behaviors for generated views")

    # Type mappings
    type_mapping = CommentedSeq()

    # TIMESTAMP mapping
    timestamp_mapping = CommentedMap()
    timestamp_mapping["bq_type"] = "TIMESTAMP"
    timestamp_mapping["lookml_type"] = "dimension_group"
    timestamp_params = CommentedMap()
    timestamp_params["type"] = "time"
    timestamp_params["timeframes"] = "[raw, time, date, week, month, quarter, year]"
    timestamp_params["sql"] = "${TABLE}.%s"
    timestamp_mapping["lookml_params"] = timestamp_params
    type_mapping.append(timestamp_mapping)

    # DATE mapping
    date_mapping = CommentedMap()
    date_mapping["bq_type"] = "DATE"
    date_mapping["lookml_type"] = "dimension_group"
    date_params = CommentedMap()
    date_params["type"] = "time"
    date_params["timeframes"] = "[date, week, month, quarter, year]"
    date_params["sql"] = "${TABLE}.%s"
    date_mapping["lookml_params"] = date_params
    type_mapping.append(date_mapping)

    # INTEGER mapping
    integer_mapping = CommentedMap()
    integer_mapping["bq_type"] = "INTEGER"
    integer_mapping["lookml_type"] = "dimension"
    integer_params = CommentedMap()
    integer_params["type"] = "number"
    integer_mapping["lookml_params"] = integer_params
    type_mapping.append(integer_mapping)

    # INT64 mapping
    int64_mapping = CommentedMap()
    int64_mapping["bq_type"] = "INT64"
    int64_mapping["lookml_type"] = "dimension"
    int64_params = CommentedMap()
    int64_params["type"] = "number"
    int64_mapping["lookml_params"] = int64_params
    type_mapping.append(int64_mapping)

    # FLOAT64 mapping
    float64_mapping = CommentedMap()
    float64_mapping["bq_type"] = "FLOAT64"
    float64_mapping["lookml_type"] = "dimension"
    float64_params = CommentedMap()
    float64_params["type"] = "number"
    float64_mapping["lookml_params"] = float64_params
    type_mapping.append(float64_mapping)

    # NUMERIC mapping
    numeric_mapping = CommentedMap()
    numeric_mapping["bq_type"] = "NUMERIC"
    numeric_mapping["lookml_type"] = "dimension"
    numeric_params = CommentedMap()
    numeric_params["type"] = "number"
    numeric_mapping["lookml_params"] = numeric_params
    type_mapping.append(numeric_mapping)

    # STRING mapping
    string_mapping = CommentedMap()
    string_mapping["bq_type"] = "STRING"
    string_mapping["lookml_type"] = "dimension"
    string_params = CommentedMap()
    string_params["type"] = "string"
    string_mapping["lookml_params"] = string_params
    type_mapping.append(string_mapping)

    # BOOL mapping
    bool_mapping = CommentedMap()
    bool_mapping["bq_type"] = "BOOL"
    bool_mapping["lookml_type"] = "dimension"
    bool_params = CommentedMap()
    bool_params["type"] = "yesno"
    bool_mapping["lookml_params"] = bool_params
    type_mapping.append(bool_mapping)

    # GEOGRAPHY mapping
    geography_mapping = CommentedMap()
    geography_mapping["bq_type"] = "GEOGRAPHY"
    geography_mapping["lookml_type"] = "dimension"
    geography_params = CommentedMap()
    geography_params["type"] = "string"
    geography_mapping["lookml_params"] = geography_params
    type_mapping.append(geography_mapping)

    model_rules["type_mapping"] = type_mapping
    model_rules.yaml_set_comment_before_after_key(
        "type_mapping",
        before="Rules for mapping warehouse data types to LookML types and parameters",
    )

    config["model_rules"] = model_rules
    config.yaml_set_comment_before_after_key("model_rules", before="Rules for how models and fields are generated")

    return config


def write_yaml_with_comments(config: CommentedMap, file_path: str):
    """Write YAML file with proper formatting and comments using ruamel.yaml."""
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.default_flow_style = False
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.width = 4096  # Prevent line wrapping

    with open(file_path, "w") as f:
        yaml.dump(config, f)
