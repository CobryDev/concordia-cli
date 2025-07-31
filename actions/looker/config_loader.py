import os
import yaml
import json
from pathlib import Path
from typing import Dict, Any, Optional
import click
from google.auth import default
from google.oauth2 import service_account


class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing."""
    pass


def load_config(config_path: str = "concordia.yaml") -> Dict[str, Any]:
    """
    Load and validate the concordia.yaml configuration file.

    Args:
        config_path: Path to the configuration file

    Returns:
        Dict containing the parsed configuration

    Raises:
        ConfigurationError: If configuration is missing or invalid
    """
    if not os.path.exists(config_path):
        raise ConfigurationError(
            f"Configuration file '{config_path}' not found. "
            "Run 'concordia init' to create it."
        )

    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigurationError(f"Invalid YAML in configuration file: {e}")

    # Validate required sections
    _validate_config(config)

    return config


def _validate_config(config: Dict[str, Any]) -> None:
    """Validate that the configuration contains required sections."""
    required_sections = ['connection', 'looker', 'model_rules']

    for section in required_sections:
        if section not in config:
            raise ConfigurationError(
                f"Missing required section '{section}' in configuration")

    # Validate connection section
    connection = config['connection']
    if 'datasets' not in connection or not connection['datasets']:
        raise ConfigurationError(
            "At least one dataset must be specified in connection.datasets")

    # Validate looker section
    looker = config['looker']
    required_looker_fields = ['project_path',
                              'views_path', 'explores_path', 'connection']
    for field in required_looker_fields:
        if field not in looker:
            raise ConfigurationError(
                f"Missing required field 'looker.{field}' in configuration")


def get_bigquery_credentials(config: Dict[str, Any]) -> tuple:
    """
    Get BigQuery credentials from configuration.

    Args:
        config: The loaded configuration dictionary

    Returns:
        Tuple of (credentials, project_id)

    Raises:
        ConfigurationError: If credentials cannot be obtained
    """
    connection = config['connection']

    # Method 1: Try to load from Dataform credentials file
    if 'dataform_credentials_file' in connection:
        creds_path = connection['dataform_credentials_file']
        if os.path.exists(creds_path):
            try:
                credentials, project_id = _load_dataform_credentials(
                    creds_path)
                # Use project_id from config if provided, otherwise from credentials
                config_project_id = connection.get('project_id')
                if config_project_id and config_project_id != 'your-gcp-project-id':
                    project_id = config_project_id
                return credentials, project_id
            except Exception as e:
                click.echo(f"⚠️  Failed to load Dataform credentials: {e}")
                click.echo(
                    "Falling back to Application Default Credentials...")

    # Method 2: Use Application Default Credentials
    try:
        credentials, default_project = default()
        project_id = connection.get('project_id', default_project)

        if not project_id or project_id == 'your-gcp-project-id':
            raise ConfigurationError(
                "No valid project_id found. Please set 'connection.project_id' in your configuration."
            )

        return credentials, project_id
    except Exception as e:
        raise ConfigurationError(
            f"Failed to obtain Google credentials: {e}. "
            "Ensure you have valid Dataform credentials or have run 'gcloud auth application-default login'."
        )


def _load_dataform_credentials(creds_path: str) -> tuple:
    """
    Load credentials from a Dataform credentials file.

    Args:
        creds_path: Path to the Dataform credentials JSON file

    Returns:
        Tuple of (credentials, project_id)
    """
    with open(creds_path, 'r') as f:
        dataform_config = json.load(f)

    # Extract the credentials section from Dataform config
    if 'credentials' not in dataform_config:
        raise ConfigurationError(
            "No 'credentials' section found in Dataform credentials file")

    creds_data = dataform_config['credentials']

    # Create service account credentials
    credentials = service_account.Credentials.from_service_account_info(
        creds_data)

    # Extract project ID
    project_id = creds_data.get('project_id')
    if not project_id:
        raise ConfigurationError(
            "No 'project_id' found in Dataform credentials")

    return credentials, project_id


def get_bigquery_location(config: Dict[str, Any]) -> Optional[str]:
    """Get BigQuery location from configuration."""
    location = config['connection'].get('location')
    if location and location != 'your-region':
        return location
    return None
