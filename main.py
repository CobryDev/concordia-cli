import click

from actions.help import show_help
from actions.init import run_initialization
from actions.looker import generate_lookml


@click.group()
def cli():
    """Concordia CLI - Generate LookML from your data warehouse."""
    pass


@cli.command()
@click.option("--force", is_flag=True, help="Overwrite existing concordia.yaml file")
def init(force):
    """Initialize a new concordia.yaml configuration file."""
    run_initialization(force)


@cli.command()
def help():
    """Show comprehensive help for Concordia CLI."""
    show_help()


@cli.group()
def looker():
    """Looker-related commands."""
    pass


@looker.command()
def generate():
    """Generate LookML views from BigQuery tables."""
    generate_lookml()


if __name__ == "__main__":
    cli()
