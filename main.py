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
def config():
    """Configuration management commands."""
    pass


@config.command()
@click.option("--file", "-f", default="concordia.yaml", help="Path to configuration file")
@click.option("--strict", is_flag=True, help="Use strict validation (for production)")
@click.option("--schema", is_flag=True, help="Output JSON schema instead of validating")
def validate(file, strict, schema):
    """Validate concordia.yaml configuration file."""
    import json

    from actions.utils.config_validator import generate_json_schema, validate_config_file

    if schema:
        # Generate and output JSON schema
        schema_data = generate_json_schema()
        click.echo(json.dumps(schema_data, indent=2))
        return

    # Validate configuration file
    click.echo(f"🔍 Validating configuration file: {file}")
    if strict:
        click.echo("📋 Using strict validation (production mode)")
    else:
        click.echo("📋 Using lenient validation (development mode)")

    result = validate_config_file(file, strict=strict)

    if result["success"]:
        click.echo(f"✅ {result['message']}")

        if result["warnings"]:
            click.echo(f"\n⚠️  Found {len(result['warnings'])} warnings:")
            for warning in result["warnings"]:
                click.echo(f"  • {warning}")
            click.echo("\nThese warnings indicate template values or missing files.")
            click.echo("The configuration will work for testing but should be updated for production use.")
    else:
        click.echo(f"❌ {result['message']}")

        if result["errors"]:
            click.echo(f"\nErrors ({len(result['errors'])}):")
            for error in result["errors"]:
                click.echo(f"  • {error}")

        if result["warnings"]:
            click.echo(f"\nWarnings ({len(result['warnings'])}):")
            for warning in result["warnings"]:
                click.echo(f"  • {warning}")

        # Exit with error code
        raise click.ClickException("Configuration validation failed")


@config.command()
@click.option("--output", "-o", default="CONFIG.md", help="Output file for documentation")
def docs(output):
    """Generate configuration documentation."""
    from actions.utils.config_docs import save_config_docs

    click.echo("📝 Generating configuration documentation...")
    save_config_docs(output)
    click.echo(f"✅ Documentation saved to: {output}")

    # Show a preview of what was generated
    click.echo("\n📖 Documentation includes:")
    click.echo("  • Complete configuration reference")
    click.echo("  • Field-by-field explanations with examples")
    click.echo("  • Validation rules and requirements")
    click.echo("  • Troubleshooting guide")
    click.echo("  • BigQuery to LookML type mapping guide")


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
