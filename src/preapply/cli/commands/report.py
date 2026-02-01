"""Report command - generate reports from CoreOutput (read-only)."""

import json
from pathlib import Path
import click
from ...contracts.core_output import CoreOutput
from ...report.github import format_github_comment, post_pr_comment
from ...report.markdown import generate_markdown
from ...report.artifact import generate_artifacts
from ...utils.errors import PreApplyError
from ...utils.logging import get_logger
from ..utils import format_error

logger = get_logger("cli.report")


@click.group()
def report():
    """Generate reports from PreApply analysis (read-only)."""
    pass


@report.command()
@click.option('--core-output', '-i', required=True, type=click.Path(exists=True), help='Path to CoreOutput JSON file')
@click.option('--repo', required=True, help='GitHub repository (owner/repo)')
@click.option('--pr', required=True, type=int, help='Pull request number')
@click.option('--token', envvar='GITHUB_TOKEN', help='GitHub token (or use GITHUB_TOKEN env var)')
@click.option('--update', is_flag=True, help='Update existing comment if found')
def github(core_output, repo, pr, token, update):
    """Post PreApply analysis as GitHub PR comment."""
    try:
        # Load CoreOutput
        core_output_path = Path(core_output)
        with open(core_output_path, 'r', encoding='utf-8') as f:
            output_data = json.load(f)
        output = CoreOutput(**output_data)
        
        # Format comment
        comment = format_github_comment(output)
        
        # Check for token
        if not token:
            click.echo(format_error("GitHub token required. Set GITHUB_TOKEN environment variable or use --token option."), err=True)
            click.get_current_context().exit(1)
        
        # Post comment
        post_pr_comment(repo, pr, comment, token, update=update)
        click.echo(f"Posted PreApply comment to {repo}#{pr}", err=True)
    
    except PreApplyError as e:
        click.echo(format_error(str(e)), err=True)
        click.get_current_context().exit(1)
    except json.JSONDecodeError as e:
        click.echo(format_error(f"Invalid JSON in CoreOutput file: {e}"), err=True)
        click.get_current_context().exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        click.echo(format_error(f"Failed to post GitHub comment: {e}"), err=True)
        click.get_current_context().exit(1)


@report.command()
@click.option('--core-output', '-i', required=True, type=click.Path(exists=True), help='Path to CoreOutput JSON file')
@click.option('--output', '-o', required=True, type=click.Path(), help='Output markdown file path')
def markdown(core_output, output):
    """Generate markdown report from CoreOutput."""
    try:
        # Load CoreOutput
        core_output_path = Path(core_output)
        with open(core_output_path, 'r', encoding='utf-8') as f:
            output_data = json.load(f)
        output_obj = CoreOutput(**output_data)
        
        # Generate markdown
        output_path = Path(output)
        generate_markdown(output_obj, output_path)
        
        click.echo(f"Generated markdown report: {output_path}", err=True)
    
    except PreApplyError as e:
        click.echo(format_error(str(e)), err=True)
        click.get_current_context().exit(1)
    except json.JSONDecodeError as e:
        click.echo(format_error(f"Invalid JSON in CoreOutput file: {e}"), err=True)
        click.get_current_context().exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        click.echo(format_error(f"Failed to generate markdown report: {e}"), err=True)
        click.get_current_context().exit(1)


@report.command()
@click.option('--core-output', '-i', required=True, type=click.Path(exists=True), help='Path to CoreOutput JSON file')
@click.option('--output', '-o', required=True, type=click.Path(), help='Output directory for artifacts')
def artifact(core_output, output):
    """Generate CI/CD artifacts from CoreOutput."""
    try:
        # Load CoreOutput
        core_output_path = Path(core_output)
        with open(core_output_path, 'r', encoding='utf-8') as f:
            output_data = json.load(f)
        output_obj = CoreOutput(**output_data)
        
        # Generate artifacts
        output_dir = Path(output)
        generate_artifacts(output_obj, output_dir)
        
        click.echo(f"Generated artifacts in: {output_dir}", err=True)
    
    except PreApplyError as e:
        click.echo(format_error(str(e)), err=True)
        click.get_current_context().exit(1)
    except json.JSONDecodeError as e:
        click.echo(format_error(f"Invalid JSON in CoreOutput file: {e}"), err=True)
        click.get_current_context().exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        click.echo(format_error(f"Failed to generate artifacts: {e}"), err=True)
        click.get_current_context().exit(1)
