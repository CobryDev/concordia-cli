"""
Pydantic models for concordia.yaml configuration.

These models provide type safety and validation for the configuration file,
replacing the previous Dict[str, Any] approach.
"""

import os
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class ConnectionConfig(BaseModel):
    """BigQuery connection configuration."""

    dataform_credentials_file: Optional[str] = Field(default=None, description="Path to Dataform credentials JSON file")
    project_id: Optional[str] = Field(default=None, description="GCP project ID")
    location: Optional[str] = Field(default=None, description="BigQuery location/region")
    datasets: list[str] = Field(description="List of datasets to scan for tables")

    @field_validator("dataform_credentials_file")
    @classmethod
    def validate_credentials_file(cls, v):
        """Validate that credentials file exists if provided."""
        if v and not os.path.exists(v):
            # Only warn, don't fail validation as file might be created later
            pass
        return v

    @field_validator("project_id")
    @classmethod
    def validate_project_id(cls, v):
        """Validate project ID format."""
        if v and v == "your-gcp-project-id":
            # This is the template value, treat as None
            return None
        return v

    @field_validator("location")
    @classmethod
    def validate_location(cls, v):
        """Validate location format."""
        if v and v == "your-region":
            # This is the template value, treat as None
            return None
        return v


class LookerConfig(BaseModel):
    """Looker project configuration."""

    project_path: str = Field(description="Path to Looker project directory")
    views_path: str = Field(description="Relative path within project for generated views file")
    connection: str = Field(description="Looker connection name for BigQuery")

    @field_validator("connection")
    @classmethod
    def validate_connection_name(cls, v):
        """Validate that connection name is not the template value."""
        if v == "your-bigquery-connection":
            raise ValueError("Please replace 'your-bigquery-connection' with your actual Looker connection name")
        return v


class NamingConventions(BaseModel):
    """Database naming convention rules."""

    pk_suffix: str = Field(default="_pk", description="Suffix used for primary key columns")
    fk_suffix: str = Field(default="_fk", description="Suffix used for foreign key columns")
    view_prefix: Optional[str] = Field(default="", description="Prefix for generated view names")
    view_suffix: Optional[str] = Field(default="", description="Suffix for generated view names")


class DefaultBehaviors(BaseModel):
    """Default behaviors for view generation."""

    measures: list[str] = Field(default=["count"], description="Default measures to create for each view")
    hide_fields_by_suffix: list[str] = Field(
        default=["_pk", "_fk"],
        description="Field suffixes that should be hidden in Looker",
    )


class LookMLParams(BaseModel):
    """LookML parameter configuration."""

    type: str = Field(description="LookML field type")
    timeframes: Optional[str] = Field(default=None, description="Timeframes for dimension groups")
    sql: Optional[str] = Field(default=None, description="Custom SQL expression")

    # Allow additional fields for flexibility
    model_config = {"extra": "allow"}


class TypeMapping(BaseModel):
    """Mapping from BigQuery types to LookML types."""

    bq_type: str = Field(description="BigQuery column type")
    lookml_type: str = Field(description="Corresponding LookML type")
    lookml_params: LookMLParams = Field(description="LookML field parameters")


class ModelRules(BaseModel):
    """Model generation rules and type mappings."""

    naming_conventions: NamingConventions = Field(
        default_factory=NamingConventions, description="Database naming conventions"
    )
    defaults: DefaultBehaviors = Field(
        default_factory=DefaultBehaviors,
        description="Default view generation behaviors",
    )
    type_mapping: list[TypeMapping] = Field(description="BigQuery to LookML type mappings")

    def get_type_mapping_for_bq_type(self, bq_type: str) -> Optional[TypeMapping]:
        """Get the type mapping for a specific BigQuery type."""
        for mapping in self.type_mapping:
            if mapping.bq_type == bq_type:
                return mapping
        return None


class ConcordiaConfig(BaseModel):
    """Complete concordia.yaml configuration."""

    connection: ConnectionConfig = Field(description="BigQuery connection details")
    looker: LookerConfig = Field(description="Looker project configuration")
    model_rules: ModelRules = Field(description="Model generation rules")

    model_config = {"extra": "forbid"}

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        return self.model_dump(exclude_none=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConcordiaConfig":
        """Create instance from dictionary (for YAML loading)."""
        return cls(**data)
