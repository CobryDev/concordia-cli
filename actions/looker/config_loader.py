import json
import os
from typing import Any, Optional

import click
import yaml
from google.auth import default
from google.oauth2 import service_account
from pydantic import ValidationError

from ..models.config import ConcordiaConfig


class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing."""

    pass


def load_config(config_path: str = "concordia.yaml") -> ConcordiaConfig:
    """
    Load and validate the concordia.yaml configuration file.

    Args:
        config_path: Path to the configuration file

    Returns:
        ConcordiaConfig object containing the parsed and validated configuration

    Raises:
        ConfigurationError: If configuration is missing or invalid
    """
    if not os.path.exists(config_path):
        raise ConfigurationError(f"Configuration file '{config_path}' not found. Run 'concordia init' to create it.")

    try:
        with open(config_path) as f:
            config_data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigurationError(f"Invalid YAML in configuration file: {e}") from e

    # Parse and validate using Pydantic model
    try:
        config = ConcordiaConfig.from_dict(config_data)
    except ValidationError as e:
        error_messages = []
        for error in e.errors():
            field_path = ".".join(str(loc) for loc in error["loc"])
            error_messages.append(f"{field_path}: {error['msg']}")
        raise ConfigurationError(
            "Configuration validation failed:\n" + "\n".join(f"  - {msg}" for msg in error_messages)
        ) from e

    return config


# Note: Configuration validation is now handled by Pydantic models
# The _validate_config function is no longer needed as validation
# is performed automatically when creating ConcordiaConfig instances


def get_bigquery_credentials(config: ConcordiaConfig) -> tuple:
    """
    Get BigQuery credentials from configuration.

    Args:
        config: The loaded ConcordiaConfig object

    Returns:
        Tuple of (credentials, project_id)

    Raises:
        ConfigurationError: If credentials cannot be obtained
    """
    connection = config.connection

    # Method 1: Try to load from Dataform credentials file
    if connection.dataform_credentials_file:
        creds_path = connection.dataform_credentials_file
        if os.path.exists(creds_path):
            try:
                credentials, project_id = _load_dataform_credentials(creds_path)
                # Use project_id from config if provided, otherwise from credentials
                if connection.project_id:
                    project_id = connection.project_id
                return credentials, project_id
            except Exception as e:
                click.echo(f"⚠️  Failed to load Dataform credentials: {e}")
                click.echo("Falling back to Application Default Credentials...")

    # Method 2: Use Application Default Credentials
    try:
        credentials, default_project = default()
        project_id = connection.project_id or default_project

        if not project_id:
            raise ConfigurationError(
                "No valid project_id found. Please set 'connection.project_id' in your configuration."
            )

        return credentials, project_id
    except Exception as e:
        raise ConfigurationError(
            f"Failed to obtain Google credentials: {e}. "
            "Ensure you have valid Dataform credentials or have run "
            "'gcloud auth application-default login'."
        ) from e


def _parse_dataform_config(creds_path: str) -> dict[str, Any]:
    """
    Parse a Dataform credentials file and extract configuration.

    Args:
        creds_path: Path to the Dataform credentials JSON file

    Returns:
        Dictionary containing parsed configuration

    Raises:
        ConfigurationError: If file cannot be parsed
    """
    with open(creds_path) as f:
        dataform_config = json.load(f)

    return dataform_config


def _load_dataform_credentials(creds_path: str) -> tuple:
    """
    Load credentials from a Dataform credentials file.

    Supports two formats:
    1. Service account format: {"credentials": {...service account info...}}
    2. Simple format: {"projectId": "...", "location": "..."}

    Args:
        creds_path: Path to the Dataform credentials JSON file

    Returns:
        Tuple of (credentials, project_id)
    """
    dataform_config = _parse_dataform_config(creds_path)

    # Format 1: Service account credentials with nested 'credentials' key
    if "credentials" in dataform_config:
        creds_data = dataform_config["credentials"]

        # Some Dataform exports store the service account JSON as a string.
        # If so, parse it into a dict before constructing credentials.
        if isinstance(creds_data, str):
            try:
                creds_data = json.loads(creds_data)
            except json.JSONDecodeError as e:
                raise ConfigurationError(f"Invalid 'credentials' JSON string in Dataform credentials file: {e}") from e

        # Create service account credentials
        credentials = service_account.Credentials.from_service_account_info(creds_data)

        # Extract project ID
        project_id = creds_data.get("project_id")
        if not project_id:
            raise ConfigurationError("No 'project_id' found in Dataform credentials")

        return credentials, project_id

    # Format 2: Simple format with projectId and location at root level
    elif "projectId" in dataform_config:
        # For simple format, we need to use Application Default Credentials
        # but extract the project ID from the file
        project_id = dataform_config["projectId"]

        try:
            # Use Application Default Credentials
            credentials, _ = default()
            return credentials, project_id
        except Exception as e:
            raise ConfigurationError(
                f"Failed to load Application Default Credentials: {e}. "
                "Please run 'gcloud auth application-default login'."
            ) from e

    else:
        raise ConfigurationError(
            "Invalid credentials file format. Expected either 'credentials' "
            "section (service account) or 'projectId' field (simple format)."
        )


def get_bigquery_location(config: ConcordiaConfig) -> Optional[str]:
    """
    Get BigQuery location from configuration.

    Checks both the configuration file and the credentials file for location.
    """
    connection = config.connection

    # First, check the config file
    if connection.location:
        return connection.location

    # If not found in config, try to get it from the credentials file
    if connection.dataform_credentials_file:
        creds_path = connection.dataform_credentials_file
        if os.path.exists(creds_path):
            try:
                dataform_config = _parse_dataform_config(creds_path)
                # Check for location in the credentials file
                creds_location = dataform_config.get("location")
                if creds_location:
                    return creds_location
            except (OSError, json.JSONDecodeError, KeyError, TypeError) as e:
                # If we can't parse the credentials file, continue without location (optional)
                click.echo(f"⚠️  Unable to read location from credentials at '{creds_path}': {e}")

    return None
