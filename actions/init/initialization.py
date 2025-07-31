import os
import click
from pathlib import Path
from typing import Optional

from .config import generate_concordia_config, write_yaml_with_comments


def find_file_in_tree(filename: str, start_path: str = ".") -> Optional[str]:
    """
    Search for a file recursively starting from start_path.
    Returns the relative path to the directory containing the file, or None if not found.
    """
    start_path_obj = Path(start_path)

    # Search in current directory and all subdirectories
    for root, dirs, files in os.walk(start_path):
        if filename in files:
            # Convert to Path for better cross-platform handling
            root_path = Path(root)
            # Return path relative to the start_path, not the current working directory
            try:
                relative_path = root_path.relative_to(start_path_obj.resolve())
                # If it's the same directory, return just the directory name
                if relative_path == Path('.'):
                    return start_path_obj.name if start_path_obj.name != '.' else '.'
                # Normalize to forward slashes
                return str(relative_path).replace('\\', '/')
            except ValueError:
                # Fallback to relative path from current working directory
                return os.path.relpath(root).replace('\\', '/')

    return None


def handle_gitignore():
    """Create or update .gitignore to include Dataform credentials file."""
    gitignore_path = '.gitignore'
    gitignore_entry = '.df-credentials.json'

    if os.path.exists(gitignore_path):
        # Read existing .gitignore
        with open(gitignore_path, 'r') as f:
            content = f.read()

        # Check if entry already exists
        if gitignore_entry in content:
            try:
                click.echo(f"✅ {gitignore_entry} already in .gitignore")
            except UnicodeEncodeError:
                click.echo(f"[PASS] {gitignore_entry} already in .gitignore")
            return

        # Add entry to existing .gitignore
        with open(gitignore_path, 'a') as f:
            if not content.endswith('\n'):
                f.write('\n')
            f.write(f'{gitignore_entry}\n')

        try:
            click.echo(f"✅ Added {gitignore_entry} to existing .gitignore")
        except UnicodeEncodeError:
            click.echo(
                f"[PASS] Added {gitignore_entry} to existing .gitignore")
    else:
        # Create new .gitignore
        with open(gitignore_path, 'w') as f:
            f.write(f'# Dataform credentials\n{gitignore_entry}\n')

        try:
            click.echo(f"✅ Created .gitignore with {gitignore_entry}")
        except UnicodeEncodeError:
            click.echo(f"[PASS] Created .gitignore with {gitignore_entry}")


def scan_for_projects():
    """Scan for Dataform and Looker projects and return their paths."""
    try:
        click.echo("🔍 Scanning for Dataform and Looker projects...")
    except UnicodeEncodeError:
        click.echo("[SCAN] Scanning for Dataform and Looker projects...")

    # Search for Dataform project (workflow_settings.yaml) in root directory only
    dataform_path = None
    if os.path.exists('workflow_settings.yaml'):
        dataform_path = '.'  # Root directory
        try:
            click.echo(f"✅ Found Dataform project in: {dataform_path}")
        except UnicodeEncodeError:
            click.echo(f"[PASS] Found Dataform project in: {dataform_path}")
    else:
        try:
            click.echo(
                "❌ No Dataform project found (workflow_settings.yaml not found in root)")
        except UnicodeEncodeError:
            click.echo(
                "[FAIL] No Dataform project found (workflow_settings.yaml not found in root)")

    # Search for Looker project (manifest.lkml)
    looker_path = find_file_in_tree('manifest.lkml')
    if looker_path:
        try:
            click.echo(f"✅ Found Looker project in: {looker_path}")
        except UnicodeEncodeError:
            click.echo(f"[PASS] Found Looker project in: {looker_path}")
    else:
        try:
            click.echo("❌ No Looker project found (manifest.lkml not found)")
        except UnicodeEncodeError:
            click.echo(
                "[FAIL] No Looker project found (manifest.lkml not found)")

    return dataform_path, looker_path


def show_init_summary(dataform_path: Optional[str], looker_path: Optional[str]) -> bool:
    """Show what will be created and ask for confirmation."""
    try:
        click.echo("\n📋 Concordia Initialization Summary")
    except UnicodeEncodeError:
        click.echo("\n[INIT] Concordia Initialization Summary")
    click.echo("=" * 40)

    click.echo("\nThe following will be created/updated:")
    click.echo("• concordia.yaml configuration file")
    click.echo("• .gitignore (to protect credentials)")

    if dataform_path or looker_path:
        click.echo("\nAuto-detected projects:")
        if dataform_path:
            click.echo(f"• Dataform project: {dataform_path}")
            click.echo(
                "  → Will set dataform_credentials_file to './.df-credentials.json'")
        if looker_path:
            click.echo(f"• Looker project: {looker_path}")
            click.echo(f"  → Will set project_path to './{looker_path}/'")

    click.echo("\nYou will still need to manually configure:")
    if not dataform_path:
        click.echo("• Dataform credentials file path")
    click.echo("• GCP project ID and location")
    click.echo("• BigQuery datasets to scan")
    if not looker_path:
        click.echo("• Looker project path")
    click.echo("• Looker BigQuery connection name")

    click.echo("\n" + "=" * 40)

    return click.confirm("Do you want to proceed with initialization?")


def create_configuration_file(dataform_path: Optional[str], looker_path: Optional[str], config_file: str):
    """Generate and write the concordia.yaml configuration file."""
    config = generate_concordia_config(dataform_path, looker_path)
    write_yaml_with_comments(config, config_file)


def show_next_steps(dataform_path: Optional[str], looker_path: Optional[str]):
    """Display next steps based on what was detected."""
    if not dataform_path or not looker_path:
        click.echo("\n⚠️  Manual configuration required:")
        if not dataform_path:
            click.echo(
                "   • Update dataform_credentials_file path in concordia.yaml")
            click.echo("   • Set your GCP project_id and location")
            click.echo("   • Configure your BigQuery datasets")
        if not looker_path:
            click.echo("   • Update looker.project_path in concordia.yaml")
            click.echo("   • Set your Looker connection name")
    else:
        click.echo("\n📝 Next steps:")
        click.echo("   • Review and update the generated configuration")
        click.echo("   • Set your GCP project_id and location")
        click.echo("   • Configure your BigQuery datasets")
        click.echo("   • Set your Looker connection name")


def run_initialization(force: bool = False):
    """
    Main initialization function that orchestrates the entire process.

    Args:
        force: Whether to overwrite existing concordia.yaml file
    """
    config_file = 'concordia.yaml'

    # Check if config file already exists
    if os.path.exists(config_file) and not force:
        click.echo(
            f"Error: {config_file} already exists. Use --force to overwrite.")
        return

    # Scan for projects
    dataform_path, looker_path = scan_for_projects()

    # Show summary and get confirmation
    if not show_init_summary(dataform_path, looker_path):
        try:
            click.echo("❌ Initialization cancelled.")
        except UnicodeEncodeError:
            click.echo("[FAIL] Initialization cancelled.")
        return

    try:
        # Handle .gitignore
        handle_gitignore()

        # Create configuration file
        create_configuration_file(dataform_path, looker_path, config_file)
        try:
            click.echo(f"\n🎉 Created {config_file}")
        except UnicodeEncodeError:
            click.echo(f"\n[SUCCESS] Created {config_file}")

        # Show next steps
        show_next_steps(dataform_path, looker_path)

        try:
            click.echo(f"\n🚀 Concordia initialization complete!")
        except UnicodeEncodeError:
            click.echo(f"\n[COMPLETE] Concordia initialization complete!")

    except Exception as e:
        click.echo(f"Error during initialization: {e}")
        raise click.ClickException(f"Initialization failed: {e}")
