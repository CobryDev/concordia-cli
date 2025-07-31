import click
from pathlib import Path
from .config_loader import load_config, get_bigquery_credentials, get_bigquery_location, ConfigurationError
from .bigquery_client import BigQueryClient
from .lookml_generator import LookMLGenerator, LookMLFileWriter


def generate_lookml():
    """Generate LookML views from BigQuery tables."""
    click.echo("🚀 Starting LookML generation...")

    try:
        # Load configuration
        click.echo("📋 Loading configuration...")
        config = load_config()

        # Get BigQuery credentials and connection info
        click.echo("🔐 Setting up BigQuery connection...")
        credentials, project_id = get_bigquery_credentials(config)
        location = get_bigquery_location(config)
        datasets = config['connection']['datasets']

        # Initialize BigQuery client
        bq_client = BigQueryClient(credentials, project_id, location, config)

        # Test connection
        click.echo("🔗 Testing BigQuery connection...")
        if not bq_client.test_connection(datasets):
            click.echo(
                "❌ BigQuery connection test failed. Please check your configuration.")
            return

        # Extract table metadata using INFORMATION_SCHEMA
        click.echo("🔍 Extracting table metadata...")
        tables_metadata = bq_client.get_tables_metadata(datasets)

        # Get error tracker for summary reporting
        error_tracker = bq_client.get_error_tracker()

        if not tables_metadata:
            click.echo("❌ No tables found in the specified datasets.")
            # Still show error summary even if no tables found
            error_tracker.print_summary(len(datasets), 0)
            return

        click.echo(f"📊 Found {len(tables_metadata)} tables to process")

        # Initialize generators
        generator = LookMLGenerator(config)
        file_writer = LookMLFileWriter(config)

        # Generate LookML project using dictionary-based approach
        click.echo("⚙️  Generating LookML project...")
        project_dict = generator.generate_complete_lookml_project(
            tables_metadata)

        # Show what files will be generated
        if project_dict:
            click.echo("\n📁 Files to be generated:")
            project_path = Path(config['looker']['project_path'])

            if 'view' in project_dict:
                views_file = project_path / config['looker']['views_path']
                click.echo(f"   Views: {views_file}")

            if 'explore' in project_dict:
                explores_file = project_path / \
                    config['looker']['explores_path']
                click.echo(f"   Explores: {explores_file}")

        # Write the complete project
        if project_dict:
            output_files = file_writer.write_complete_project(project_dict)

            click.echo("📁 Generated LookML files:")
            for output_file in output_files:
                click.echo(f"   {output_file}")

            # Summary
            view_count = len(project_dict.get('view', {}))
            explore_count = len(project_dict.get('explore', {}))

            click.echo(f"\n🎉 Successfully generated LookML project!")
            click.echo(f"   Views: {view_count}")
            click.echo(f"   Explores: {explore_count}")
            click.echo(f"   Files: {len(output_files)}")
        else:
            click.echo("❌ No LookML content was generated.")

        # Show comprehensive error summary
        error_tracker.print_summary(len(datasets), len(tables_metadata))

        # Next steps
        click.echo("\n📝 Next steps:")
        click.echo("   1. Review the generated LookML files")
        click.echo("   2. Include the files in your Looker project")
        click.echo("   3. Test the views and explores in Looker")
        click.echo(
            "   4. Customize field names, descriptions, or types as needed")
        click.echo("   5. Set up relationships between explores if needed")

    except ConfigurationError as e:
        click.echo(f"❌ Configuration error: {e}")
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}")
        if click.confirm("Would you like to see the full error details?"):
            import traceback
            click.echo(traceback.format_exc())
