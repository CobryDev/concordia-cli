"""
Configuration validation utilities for Concordia.

This module provides functions to validate concordia.yaml configuration files,
including both strict validation (for production use) and lenient validation
(for initialization and template values).
"""

from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import ValidationError

from ..models.config import ConcordiaConfig


class ConfigValidationError(Exception):
    """Custom exception for configuration validation errors."""

    def __init__(self, message: str, errors: Optional[list[dict[str, Any]]] = None):
        super().__init__(message)
        self.errors = errors or []


def load_config_file(config_path: str = "concordia.yaml") -> dict[str, Any]:
    """Load configuration from YAML file.

    Args:
        config_path: Path to the configuration file

    Returns:
        Raw configuration dictionary

    Raises:
        ConfigValidationError: If file cannot be loaded or parsed
    """
    config_file = Path(config_path)

    if not config_file.exists():
        raise ConfigValidationError(
            f"Configuration file not found: {config_path}")

    try:
        with open(config_file, encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigValidationError(
            f"Invalid YAML syntax in {config_path}: {e}") from e
    except Exception as e:
        raise ConfigValidationError(f"Error reading {config_path}: {e}") from e

    if config_data is None:
        raise ConfigValidationError(
            f"Configuration file is empty: {config_path}")

    if not isinstance(config_data, dict):
        raise ConfigValidationError(
            f"Configuration must be a YAML object, got {type(config_data).__name__}")

    return config_data


def validate_config_strict(config_data: dict[str, Any]) -> ConcordiaConfig:
    """Validate configuration with strict rules.

    This validation is used during actual generation runs and requires
    all template values to be replaced with real values.

    Args:
        config_data: Raw configuration dictionary

    Returns:
        Validated ConcordiaConfig instance

    Raises:
        ConfigValidationError: If configuration is invalid
    """
    try:
        # First create the config (this allows template values)
        config = ConcordiaConfig.from_dict(config_data)

        # Then check for template values in strict mode
        errors = []

        # Check connection template values
        if config.connection.project_id in ["your-gcp-project-id", "your-project-id"]:
            errors.append({
                "location": "connection.project_id",
                "message": "Please replace template project ID with your actual GCP project ID",
                "input": config.connection.project_id,
                "type": "template_value"
            })

        if config.connection.location in ["your-region", "your-location"]:
            errors.append({
                "location": "connection.location",
                "message": "Please replace template location with your actual BigQuery location",
                "input": config.connection.location,
                "type": "template_value"
            })

        # Check Looker template values
        if config.looker.connection in ["your-bigquery-connection", "your_connection_name"]:
            errors.append({
                "location": "looker.connection",
                "message": "Please replace template connection name with your actual Looker BigQuery connection name",
                "input": config.looker.connection,
                "type": "template_value"
            })

        if errors:
            raise ConfigValidationError(
                f"Configuration has {len(errors)} template values that must be replaced",
                errors
            )

        return config

    except ValidationError as e:
        error_details = []
        for error in e.errors():
            location = " -> ".join(str(loc) for loc in error["loc"])
            error_details.append({
                "location": location,
                "message": error["msg"],
                "input": error.get("input"),
                "type": error["type"]
            })

        raise ConfigValidationError(
            f"Configuration validation failed with {len(error_details)} errors",
            error_details
        ) from e


def validate_config_lenient(config_data: dict[str, Any]) -> tuple[bool, list[str], list[str]]:
    """Validate configuration with lenient rules.

    This validation allows template values and missing files during initialization.
    Returns detailed information about validation status.

    Args:
        config_data: Raw configuration dictionary

    Returns:
        Tuple of (is_valid, warnings, errors)
        - is_valid: True if config structure is valid
        - warnings: List of warning messages (template values, missing files)
        - errors: List of error messages (structural issues)
    """
    errors = []
    warnings = []

    try:
        # Try to create the config, but catch validation errors
        config = ConcordiaConfig.from_dict(config_data)

        # Check for template values that need replacement
        warnings.extend(_check_template_values(config))

        # Check for missing files/directories (warnings, not errors)
        warnings.extend(_check_missing_paths(config))

        return True, warnings, errors

    except ValidationError as e:
        # Parse validation errors
        for error in e.errors():
            location = " -> ".join(str(loc) for loc in error["loc"])
            message = error["msg"]

            # Classify errors vs warnings
            if _is_template_value_error(error):
                warnings.append(f"{location}: {message}")
            elif _is_missing_file_error(error):
                warnings.append(f"{location}: {message}")
            else:
                errors.append(f"{location}: {message}")

        is_valid = len(errors) == 0
        return is_valid, warnings, errors

    except Exception as e:
        errors.append(f"Unexpected validation error: {e}")
        return False, warnings, errors


def _check_template_values(config: ConcordiaConfig) -> list[str]:
    """Check for template values that should be replaced."""
    warnings = []

    # Check connection template values
    if config.connection.dataform_credentials_file:
        creds_file = config.connection.dataform_credentials_file
        # Only warn about obvious template values, not actual file paths
        if creds_file in ["path/to/your/dataform-credentials.json"]:
            warnings.append(
                "connection.dataform_credentials_file: Using template value, replace with actual path")
        # For .df-credentials.json, only warn if the file doesn't exist
        elif creds_file == ".df-credentials.json" and not Path(creds_file).exists():
            warnings.append(
                "connection.dataform_credentials_file: File '.df-credentials.json' not found. "
                "Create the file or remove this setting to use Application Default Credentials.")

    if config.connection.project_id in ["your-gcp-project-id", "your-project-id"]:
        warnings.append(
            "connection.project_id: Using template value, replace with actual GCP project ID")

    if config.connection.location in ["your-region", "your-location"]:
        warnings.append(
            "connection.location: Using template value, replace with actual BigQuery location")

    # Check Looker template values
    if config.looker.project_path in ["./looker-project", "path/to/your/looker/project"]:
        warnings.append(
            "looker.project_path: Using template value, replace with actual Looker project path")

    if config.looker.views_path in ["views/concordia_views.view.lkml"]:
        warnings.append(
            "looker.views_path: Using template value, consider customizing the views file path")

    if config.looker.connection in ["your-bigquery-connection", "your_connection_name"]:
        warnings.append(
            "looker.connection: Using template value, replace with actual Looker connection name")

    return warnings


def _check_missing_paths(config: ConcordiaConfig) -> list[str]:
    """Check for missing files and directories."""
    warnings = []

    # Check credentials file (but avoid duplicate warnings with template check)
    if config.connection.dataform_credentials_file:
        creds_path = Path(config.connection.dataform_credentials_file)
        creds_file = config.connection.dataform_credentials_file
        # Only warn about missing files if it's not an obvious template value
        # and not the common .df-credentials.json case (handled in template check)
        if (not creds_path.exists() and
            creds_file not in ["path/to/your/dataform-credentials.json", ".df-credentials.json"]):
            warnings.append(
                f"connection.dataform_credentials_file: File not found: {creds_path}. "
                "Create the file or remove this setting to use Application Default Credentials.")

    # Check Looker project path
    looker_path = Path(config.looker.project_path)
    if not looker_path.exists():
        warnings.append(
            f"looker.project_path: Directory not found: {looker_path}")
    # Note: manifest.lkml is not required for a valid Looker project

    return warnings


def _is_template_value_error(error: dict[str, Any]) -> bool:
    """Check if validation error is due to template values."""
    message = error.get("msg", "").lower()
    return "template" in message or "replace" in message


def _is_missing_file_error(error: dict[str, Any]) -> bool:
    """Check if validation error is due to missing files."""
    message = error.get("msg", "").lower()
    return "not found" in message or "does not exist" in message


def generate_json_schema() -> dict[str, Any]:
    """Generate JSON schema for the configuration.

    Returns:
        JSON schema dictionary
    """
    return ConcordiaConfig.model_json_schema()


def format_validation_errors(errors: list[dict[str, Any]]) -> str:
    """Format validation errors for user-friendly display.

    Args:
        errors: List of error dictionaries from validation

    Returns:
        Formatted error string
    """
    if not errors:
        return "No errors found."

    formatted = []
    for error in errors:
        location = error.get("location", "unknown")
        message = error.get("message", "Unknown error")

        formatted.append(f"  • {location}: {message}")

    return "\n".join(formatted)


def validate_config_file(config_path: str = "concordia.yaml", strict: bool = False) -> dict[str, Any]:
    """Validate a configuration file and return detailed results.

    Args:
        config_path: Path to configuration file
        strict: Whether to use strict validation

    Returns:
        Dictionary with validation results:
        - success: bool
        - config: ConcordiaConfig (if successful)
        - errors: List[str]
        - warnings: List[str]
        - message: str
    """
    try:
        # Load the file
        config_data = load_config_file(config_path)

        if strict:
            # Strict validation
            config = validate_config_strict(config_data)
            return {
                "success": True,
                "config": config,
                "errors": [],
                "warnings": [],
                "message": "Configuration is valid and ready for use."
            }
        else:
            # Lenient validation
            is_valid, warnings, errors = validate_config_lenient(config_data)

            if is_valid:
                config = ConcordiaConfig.from_dict(config_data)
                message = "Configuration structure is valid."
                if warnings:
                    message += f" Found {len(warnings)} warnings."
            else:
                config = None
                message = f"Configuration has {len(errors)} structural errors."
                if warnings:
                    message += f" Also found {len(warnings)} warnings."

            return {
                "success": is_valid,
                "config": config,
                "errors": errors,
                "warnings": warnings,
                "message": message
            }

    except ConfigValidationError as e:
        return {
            "success": False,
            "config": None,
            "errors": [str(e)] + [err.get("message", str(err)) for err in e.errors],
            "warnings": [],
            "message": f"Configuration validation failed: {e}"
        }
    except Exception as e:
        return {
            "success": False,
            "config": None,
            "errors": [f"Unexpected error: {e}"],
            "warnings": [],
            "message": f"Validation failed with unexpected error: {e}"
        }
