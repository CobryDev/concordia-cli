import click

from initialization import run_initialization


@click.group()
def cli():
    """Concordia CLI - Generate LookML from your data warehouse."""
    pass


@cli.command()
@click.option('--force', is_flag=True, help='Overwrite existing concordia.yaml file')
def init(force):
    """Initialize a new concordia.yaml configuration file."""
    run_initialization(force)


if __name__ == '__main__':
    cli()
