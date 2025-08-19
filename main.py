import os
from datetime import datetime
from pathlib import Path

import click

from actions.help import show_help
from actions.init import run_initialization
from actions.looker import generate_lookml


def get_version_info():
    """Get version and last modified date from pyproject.toml."""
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib

    project_root = Path(__file__).parent
    pyproject_path = project_root / "pyproject.toml"

    if not pyproject_path.exists():
        return "unknown", "unknown"

    try:
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)

        version = data.get("project", {}).get("version", "unknown")

        # Get last modified date of the project root
        mtime = os.path.getmtime(project_root)
        last_modified = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")

        return version, last_modified
    except Exception:
        return "unknown", "unknown"


@click.group(invoke_without_command=True)
@click.option("--version", "-v", is_flag=True, help="Show version information")
@click.pass_context
def cli(ctx, version):
    """Concordia CLI - Generate LookML from your data warehouse."""
    if version:
        ver, last_mod = get_version_info()
        click.echo(f"Concordia CLI version {ver}")
        click.echo(f"Last modified: {last_mod}")
        return

    # Show help if no command is provided
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        return


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
