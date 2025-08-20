"""
Pydantic models for concordia.yaml configuration.

These models provide type safety and validation for the configuration file,
replacing the previous Dict[str, Any] approach.
"""

from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class ConnectionConfig(BaseModel):
    """BigQuery connection configuration.

    Configure how Concordia connects to your BigQuery instance.
    Either use Dataform credentials file or rely on Google Application Default Credentials.
    """

    dataform_credentials_file: Optional[str] = Field(
        default=None,
        description="Path to Dataform credentials JSON file. If not provided," +
        "will use Google Application Default Credentials.",
        examples=["./.df-credentials.json", "./path/to/credentials.json"],
    )
    project_id: Optional[str] = Field(
        default=None,
        description="GCP project ID. If not provided, will be extracted from credentials.",
        examples=["my-gcp-project", "analytics-prod-123"],
    )
    location: Optional[str] = Field(
        default=None,
        description="BigQuery location/region. Defaults to 'US' if not specified.",
        examples=["US", "EU", "us-central1", "europe-west1"],
    )
    datasets: list[str] = Field(
        description="List of BigQuery datasets to scan for tables. At least one dataset is required.",
        min_length=1,
        examples=[["raw_data", "staging"], ["analytics", "marts"]],
    )

    @field_validator("dataform_credentials_file")
    @classmethod
    def validate_credentials_file(cls, v):
        """Validate that credentials file exists if provided."""
        if v is None:
            return v

        # Check for obvious template values (but .df-credentials.json is a valid path)
        if v in ["path/to/your/dataform-credentials.json"]:
            # Allow template values during initialization
            return v

        # Convert to Path for better validation
        path = Path(v)

        # Check if file exists (but allow .df-credentials.json since ADC can be used as fallback)
        if not path.exists():
            if v == ".df-credentials.json":
                # This is a common path that might not exist yet, but ADC can be used as fallback
                return v
            else:
                raise ValueError(f"Dataform credentials file not found: {v}")

        # Check if it's a file (not directory)
        if not path.is_file():
            raise ValueError(f"Dataform credentials path is not a file: {v}")

        # Check file extension
        if path.suffix.lower() != ".json":
            raise ValueError(
                f"Dataform credentials file must be a .json file: {v}")

        return str(path)

    @field_validator("project_id")
    @classmethod
    def validate_project_id(cls, v):
        """Validate project ID format."""
        if v is None:
            return v

        # Check for template values
        if v in ["your-gcp-project-id", "your-project-id"]:
            # Allow template values - they will be caught by strict validation
            return v

        # Validate GCP project ID format
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError(
                f"Invalid GCP project ID format: {v}. Must contain only letters, numbers, hyphens, and underscores."
            )

        if len(v) < 6 or len(v) > 30:
            raise ValueError(
                f"GCP project ID must be between 6 and 30 characters: {v}")

        return v

    @field_validator("location")
    @classmethod
    def validate_location(cls, v):
        """Validate BigQuery location."""
        if v is None:
            return v

        # Check for template values
        if v in ["your-region", "your-location"]:
            # Allow template values - they will be caught by strict validation
            return v

        # Common BigQuery locations - not exhaustive but covers most cases
        valid_locations = {
            # Multi-regional
            "US",
            "EU",
            # Regional - Americas
            "us-central1",
            "us-east1",
            "us-east4",
            "us-west1",
            "us-west2",
            "us-west3",
            "us-west4",
            "northamerica-northeast1",
            "southamerica-east1",
            # Regional - Europe
            "europe-central2",
            "europe-north1",
            "europe-west1",
            "europe-west2",
            "europe-west3",
            "europe-west4",
            "europe-west6",
            # Regional - Asia Pacific
            "asia-east1",
            "asia-east2",
            "asia-northeast1",
            "asia-northeast2",
            "asia-northeast3",
            "asia-south1",
            "asia-southeast1",
            "asia-southeast2",
            "australia-southeast1",
        }

        if v.upper() not in valid_locations and v not in valid_locations:
            # Don't fail validation, just pass through - BigQuery will handle invalid locations
            pass

        return v

    @field_validator("datasets")
    @classmethod
    def validate_datasets(cls, v):
        """Validate dataset names."""
        if not v:
            raise ValueError("At least one dataset must be specified")

        for dataset in v:
            if not dataset.strip():
                raise ValueError(
                    "Dataset names cannot be empty or whitespace only")

            # Basic validation for BigQuery dataset naming rules
            if not dataset.replace("_", "").isalnum():
                raise ValueError(
                    f"Invalid dataset name '{dataset}'. "
                    "Dataset names must contain only letters, numbers, and underscores."
                )

        return v


class LookerConfig(BaseModel):
    """Looker project configuration.

    Configure where Concordia should write generated LookML files and which
    Looker connection to use for BigQuery access.
    """

    project_path: str = Field(
        description="Path to Looker project directory. Can be absolute or relative to concordia.yaml location.",
        examples=["./looker-project",
                  "../my-looker-project", "/path/to/looker"],
    )
    views_path: str = Field(
        description="Relative path within project for generated views file. Should end with .view.lkml",
        examples=["views/concordia_views.view.lkml",
                  "generated/bigquery_views.view.lkml"],
    )
    connection: str = Field(
        description="Looker connection name that points to your BigQuery instance",
        examples=["bigquery_connection", "prod_bigquery", "analytics_bq"],
    )

    @field_validator("project_path")
    @classmethod
    def validate_project_path(cls, v):
        """Validate Looker project path."""
        if not v.strip():
            raise ValueError("Looker project path cannot be empty")

        # Check for template values
        if v in ["path/to/your/looker/project", "./looker-project"]:
            # Allow template values during initialization
            return v

        path = Path(v)

        # Check if directory exists
        if not path.exists():
            raise ValueError(f"Looker project directory does not exist: {v}")

        if not path.is_dir():
            raise ValueError(f"Looker project path is not a directory: {v}")

        # Note: manifest.lkml is not required for a valid Looker project
        # Just ensure it's a directory that exists

        return str(path)

    @field_validator("views_path")
    @classmethod
    def validate_views_path(cls, v):
        """Validate views file path."""
        if not v.strip():
            raise ValueError("Views path cannot be empty")

        # Check for template values
        if v in ["views/concordia_views.view.lkml"]:
            # Allow template values during initialization
            return v

        if not v.endswith(".view.lkml"):
            raise ValueError(f"Views file must end with '.view.lkml': {v}")

        # Ensure it's a relative path (not absolute)
        if Path(v).is_absolute():
            raise ValueError(
                f"Views path must be relative to the Looker project directory: {v}")

        return v

    @field_validator("connection")
    @classmethod
    def validate_connection_name(cls, v):
        """Validate Looker connection name."""
        if not v.strip():
            raise ValueError("Looker connection name cannot be empty")

        # Check for template values
        if v in ["your-bigquery-connection", "your_connection_name"]:
            # Allow template values - they will be caught by strict validation
            return v

        # Basic validation for connection name format
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError(
                f"Invalid connection name '{v}'. Use only letters, numbers, underscores, and hyphens.")

        return v


class NamingConventions(BaseModel):
    """Database naming convention rules.

    Configure how Concordia identifies and handles different types of columns
    based on your database naming patterns.
    """

    pk_suffix: str = Field(
        default="_pk",
        description="Suffix used to identify primary key columns in your tables",
        examples=["_pk", "_id", "_key"],
    )
    fk_suffix: str = Field(
        default="_fk",
        description="Suffix used to identify foreign key columns in your tables",
        examples=["_fk", "_id", "_ref"],
    )
    view_prefix: Optional[str] = Field(
        default="", description="Prefix to add to all generated view names", examples=["bq_", "raw_", ""]
    )
    view_suffix: Optional[str] = Field(
        default="", description="Suffix to add to all generated view names", examples=["_view", "_base", ""]
    )


class DefaultBehaviors(BaseModel):
    """Default behaviors for view generation.

    Configure what measures and field visibility rules are applied to all generated views.
    """

    measures: list[str] = Field(
        default=["count"],
        description="Default measures to create for each view. Currently only 'count' is supported.",
        examples=[["count"], []],
    )
    hide_fields_by_suffix: list[str] = Field(
        default=["_pk", "_fk"],
        description="Field suffixes that should be hidden by default in Looker (set hidden: yes)",
        examples=[["_pk", "_fk"], ["_id", "_key"], []],
    )


class LookMLParams(BaseModel):
    """LookML parameter configuration.

    Defines the specific LookML parameters to apply to fields of this type.
    """

    type: str = Field(
        description="LookML field type (dimension, dimension_group, measure)",
        examples=["dimension", "dimension_group", "measure"],
    )
    timeframes: Optional[str] = Field(
        default=None,
        description="Comma-separated timeframes for dimension_group fields",
        examples=["time,date,week,month,quarter,year", "date,month,year"],
    )
    sql: Optional[str] = Field(
        default=None,
        description="Custom SQL expression template. Use ${TABLE}.column_name for field reference",
        examples=["${TABLE}.${FIELD}", "CAST(${TABLE}.${FIELD} as STRING)"],
    )

    # Allow additional fields for flexibility
    model_config = {"extra": "allow"}


class TypeMapping(BaseModel):
    """Mapping from BigQuery types to LookML types.

    Define how specific BigQuery column types should be converted to LookML fields.
    """

    bq_type: str = Field(
        description="BigQuery column type (as returned by INFORMATION_SCHEMA)",
        examples=["STRING", "INTEGER", "TIMESTAMP", "DATE", "FLOAT64"]
    )
    lookml_type: str = Field(
        description="Corresponding LookML field type",
        examples=["dimension", "dimension_group", "measure"]
    )
    lookml_params: LookMLParams = Field(
        description="LookML field parameters and configuration for this type mapping"
    )

    @field_validator("lookml_type")
    @classmethod
    def validate_lookml_type(cls, v):
        """Validate LookML type."""
        valid_types = {"dimension", "dimension_group", "measure"}
        if v not in valid_types:
            raise ValueError(
                f"Invalid LookML type '{v}'. Must be one of: {', '.join(valid_types)}")
        return v


class ModelRules(BaseModel):
    """Model generation rules and type mappings.

    Configure how Concordia generates LookML views from BigQuery metadata,
    including naming conventions, default behaviors, and type mappings.
    """

    naming_conventions: NamingConventions = Field(
        default_factory=NamingConventions,
        description="Database naming conventions for identifying primary/foreign keys"
    )
    defaults: DefaultBehaviors = Field(
        default_factory=DefaultBehaviors,
        description="Default view generation behaviors (measures, field visibility)"
    )
    type_mapping: list[TypeMapping] = Field(
        description="BigQuery to LookML type mappings. At least one mapping is required.",
        min_length=1
    )

    def get_type_mapping_for_bq_type(self, bq_type: str) -> Optional[TypeMapping]:
        """Get the type mapping for a specific BigQuery type."""
        for mapping in self.type_mapping:
            if mapping.bq_type == bq_type:
                return mapping
        return None


class ConcordiaConfig(BaseModel):
    """Complete concordia.yaml configuration.

    Root configuration object that contains all settings needed for Concordia
    to generate LookML views from BigQuery table metadata.
    """

    connection: ConnectionConfig = Field(
        description="BigQuery connection configuration (credentials, project, datasets)"
    )
    looker: LookerConfig = Field(
        description="Looker project configuration (paths, connection name)"
    )
    model_rules: ModelRules = Field(
        description="Model generation rules (naming conventions, type mappings)"
    )

    model_config = {"extra": "forbid"}

    @model_validator(mode='after')
    def validate_config_consistency(self):
        """Validate cross-field dependencies and consistency."""
        # Check that Looker project path and views path work together
        looker_path = Path(self.looker.project_path)
        views_file = looker_path / self.looker.views_path

        # Ensure views directory exists or can be created
        views_dir = views_file.parent
        if not views_dir.exists() and looker_path.exists():
            try:
                views_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                raise ValueError(
                    f"Cannot create views directory {views_dir}: {e}") from e

        return self

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        return self.model_dump(exclude_none=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConcordiaConfig":
        """Create instance from dictionary (for YAML loading)."""
        return cls(**data)
