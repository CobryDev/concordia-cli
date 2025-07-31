import click


def show_help():
    """Show comprehensive help for Concordia CLI."""
    help_text = """
🎯 Concordia CLI - Generate LookML from your data warehouse

COMMANDS:
  init     Initialize a new concordia.yaml configuration file
  help     Show this help message
  looker   Looker-related commands
    generate  Generate LookML views from BigQuery tables

EXAMPLES:
  concordia init                    # Initialize configuration
  concordia init --force           # Force overwrite existing config
  concordia looker generate        # Generate LookML views
  concordia help                   # Show this help

For more information about each command, use:
  concordia COMMAND --help
"""
    click.echo(help_text)
