import yaml
from typing import Optional, Dict, Any


def generate_concordia_config(dataform_path: Optional[str], looker_path: Optional[str]) -> Dict[str, Any]:
    """Generate the concordia.yaml configuration dictionary."""

    config = {
        '# concordia.yml - Generated Configuration': None,
        'connection': {
            '# Method 1 (Preferred): Point to a Dataform credentials JSON file.': None,
            '# Concordia will parse the \'credentials\' key from this file to authenticate.': None,
            '# The path should be relative to this config file.': None,
            'dataform_credentials_file': './dataform.json' if dataform_path else 'path/to/your/dataform.json',

            '# Method 2 (Fallback): If \'dataform_credentials_file\' is omitted or invalid,': None,
            '# Concordia will automatically use Google Application Default Credentials (ADC).': None,
            '# This is useful for local development or running in a configured GCP environment.': None,

            '# The GCP project ID to target. If not provided here, it will be inferred': None,
            '# from the credentials file or ADC.': None,
            'project_id': 'your-gcp-project-id',

            '# The default location/region for BigQuery jobs. If not provided, it will be': None,
            '# inferred from the credentials file.': None,
            'location': 'your-region',  # e.g., 'europe-west2'

            '# The datasets to scan for tables.': None,
            'datasets': ['dataset1', 'dataset2']
        },

        '# Looker project configuration': None,
        'looker': {
            'project_path': f'./{looker_path}/' if looker_path else './path/to/your/looker_project/',
            'views_path': 'views/base/base.view.lkml',
            'connection': 'your-bigquery-connection'  # This is the Looker connection name
        },

        '# Rules for how models and fields are generated': None,
        'model_rules': {
            '# Define how database column names are interpreted': None,
            'naming_conventions': {
                'pk_suffix': '_pk',
                'fk_suffix': '_fk'
            },

            '# Define default behaviors for generated views': None,
            'defaults': {
                'measures': ['count'],  # Automatically create a count measure
                'hide_fields_by_suffix': ['_pk', '_fk']  # Hide PKs and FKs
            },

            '# Rules for mapping warehouse data types to LookML types and parameters': None,
            'type_mapping': [
                {
                    'bq_type': 'TIMESTAMP',
                    'lookml_type': 'dimension_group',
                    'lookml_params': {
                        'type': 'time',
                        'timeframes': '[raw, time, date, week, month, quarter, year]',
                        'sql': '${TABLE}.%s'
                    }
                },
                {
                    'bq_type': 'DATE',
                    'lookml_type': 'dimension_group',
                    'lookml_params': {
                        'type': 'time',
                        'timeframes': '[date, week, month, quarter, year]',
                        'sql': '${TABLE}.%s'
                    }
                },
                {
                    'bq_type': 'INTEGER',
                    'lookml_type': 'dimension',
                    'lookml_params': {
                        'type': 'number'
                    }
                },
                {
                    'bq_type': 'STRING',
                    'lookml_type': 'dimension',
                    'lookml_params': {
                        'type': 'string'
                    }
                },
                {
                    'bq_type': 'BOOL',
                    'lookml_type': 'dimension',
                    'lookml_params': {
                        'type': 'yesno'
                    }
                }
            ]
        }
    }

    return config


class IndentedDumper(yaml.SafeDumper):
    """Custom YAML dumper to handle proper indentation and comments."""

    def increase_indent(self, flow=False, indentless=False):
        return super(IndentedDumper, self).increase_indent(flow, False)

    def write_line_break(self, data=None):
        super(IndentedDumper, self).write_line_break(data)


def write_yaml_with_comments(data: Dict[str, Any], file_path: str):
    """Write YAML file with proper formatting and comments."""

    yaml_content = []

    # Write header comment
    yaml_content.append('# concordia.yml - Generated Configuration')
    yaml_content.append('')

    # Process the main structure manually for better control
    yaml_content.append('# BigQuery Connection Details')
    yaml_content.append('connection:')
    yaml_content.append(
        '  # Method 1 (Preferred): Point to a Dataform credentials JSON file.')
    yaml_content.append(
        '  # Concordia will parse the \'credentials\' key from this file to authenticate.')
    yaml_content.append('  # The path should be relative to this config file.')
    yaml_content.append(
        f'  dataform_credentials_file: \'{data["connection"]["dataform_credentials_file"]}\'')
    yaml_content.append('')
    yaml_content.append(
        '  # Method 2 (Fallback): If \'dataform_credentials_file\' is omitted or invalid,')
    yaml_content.append(
        '  # Concordia will automatically use Google Application Default Credentials (ADC).')
    yaml_content.append(
        '  # This is useful for local development or running in a configured GCP environment.')
    yaml_content.append('')
    yaml_content.append(
        '  # The GCP project ID to target. If not provided here, it will be inferred')
    yaml_content.append('  # from the credentials file or ADC.')
    yaml_content.append(
        f'  project_id: \'{data["connection"]["project_id"]}\'')
    yaml_content.append('')
    yaml_content.append(
        '  # The default location/region for BigQuery jobs. If not provided, it will be')
    yaml_content.append('  # inferred from the credentials file.')
    yaml_content.append(f'  location: \'{data["connection"]["location"]}\'')
    yaml_content.append('')
    yaml_content.append('  # The datasets to scan for tables.')
    yaml_content.append('  datasets:')
    for dataset in data["connection"]["datasets"]:
        yaml_content.append(f'    - \'{dataset}\'')
    yaml_content.append('')

    yaml_content.append('# Looker project configuration')
    yaml_content.append('looker:')
    yaml_content.append(
        f'  project_path: \'{data["looker"]["project_path"]}\'')
    yaml_content.append(f'  views_path: \'{data["looker"]["views_path"]}\'')
    yaml_content.append(
        f'  connection: \'{data["looker"]["connection"]}\' # This is the Looker connection name')
    yaml_content.append('')

    yaml_content.append('# Rules for how models and fields are generated')
    yaml_content.append('model_rules:')
    yaml_content.append('  # Define how database column names are interpreted')
    yaml_content.append('  naming_conventions:')
    yaml_content.append(
        f'    pk_suffix: \'{data["model_rules"]["naming_conventions"]["pk_suffix"]}\'')
    yaml_content.append(
        f'    fk_suffix: \'{data["model_rules"]["naming_conventions"]["fk_suffix"]}\'')
    yaml_content.append('')
    yaml_content.append('  # Define default behaviors for generated views')
    yaml_content.append('  defaults:')
    yaml_content.append('    measures:')
    for measure in data["model_rules"]["defaults"]["measures"]:
        yaml_content.append(f'      - {measure}')
    yaml_content.append('    hide_fields_by_suffix:')
    for suffix in data["model_rules"]["defaults"]["hide_fields_by_suffix"]:
        yaml_content.append(f'      - \'{suffix}\'')
    yaml_content.append('')

    yaml_content.append(
        '  # Rules for mapping warehouse data types to LookML types and parameters')
    yaml_content.append('  type_mapping:')
    for mapping in data["model_rules"]["type_mapping"]:
        yaml_content.append(f'    - bq_type: \'{mapping["bq_type"]}\'')
        yaml_content.append(f'      lookml_type: \'{mapping["lookml_type"]}\'')
        yaml_content.append('      lookml_params:')
        for param_key, param_value in mapping["lookml_params"].items():
            if isinstance(param_value, str):
                yaml_content.append(f'        {param_key}: \'{param_value}\'')
            else:
                yaml_content.append(f'        {param_key}: {param_value}')

    with open(file_path, 'w') as f:
        f.write('\n'.join(yaml_content))
