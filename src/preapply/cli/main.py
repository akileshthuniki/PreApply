"""Main CLI entry point for PreApply."""

import click
from .commands.setup import setup
from .commands.ai import ai
from .commands.analyze import analyze
from .commands.explain import explain
from .commands.summary import summary
from .commands.policy import policy
from .commands.report import report
from .commands.ask import ask
from ..utils.logging import get_logger

try:
    from .. import __version__
except Exception as e:
    raise

logger = get_logger("cli.main")


@click.group()
@click.version_option(version=__version__, prog_name="preapply", message="%(prog)s version %(version)s")
def cli():
    """PreApply - Infrastructure risk analysis."""
    pass


cli.add_command(analyze)
cli.add_command(explain)
cli.add_command(summary)
cli.add_command(policy)
cli.add_command(report)
cli.add_command(ask)
cli.add_command(setup)
cli.add_command(ai)

# Import and add version command at the end
from .commands.version import version as version_command
cli.add_command(version_command)
