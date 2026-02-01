"""Version command - show PreApply version."""

import click
from ... import __version__


@click.command()
def version():
    """Show PreApply version."""
    click.echo(f"preapply version {__version__}")
