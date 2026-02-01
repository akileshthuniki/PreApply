"""Analyze command - run PreApply analysis on Terraform plan."""

import json
import sys
from pathlib import Path
import click
from ...contracts.core_output import CoreOutput
from ...utils.errors import PreApplyError
from ...utils.logging import get_logger
from ..utils import run_analysis, format_error
from ..utils.file_resolver import resolve_file_path

logger = get_logger("cli.analyze")


@click.command()
@click.argument('plan_json', type=click.Path(exists=False))
@click.option('--json', is_flag=True, help='Output structured JSON instead of human-readable')
@click.option('--output', '-o', type=click.Path(), help='Save output to file')
@click.option('--quiet', is_flag=True, help='Suppress progress messages')
def analyze(plan_json, json, output, quiet):
    """
    Analyze Terraform plan and show risk assessment.
    
    Accepts any filename for the Terraform plan JSON file. Use shell redirection
    to save output: preapply analyze plan.json > analysis.json
    """
    try:
        # Resolve and validate file path
        try:
            plan_path = resolve_file_path(plan_json)
        except FileNotFoundError as e:
            click.echo(format_error(str(e)), err=True)
            sys.exit(1)
        
        if not quiet:
            click.echo(f"✨ Loading and validating plan: {plan_path}", err=True)
        
        # Run analysis using shared helper
        analysis_result = run_analysis(str(plan_path))
        
        if not quiet:
            click.echo("📊 Building dependency graph and calculating risk...", err=True)
            click.echo("✅ Analysis complete!", err=True)
        
        # Format output
        if json:
            output_text = _format_json_output(analysis_result)
        else:
            from ...presentation.human_formatter import format_human_friendly
            output_text = format_human_friendly(analysis_result)
        
        # Write output
        if output:
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(output_text)
            if not quiet:
                click.echo(f"Output saved to: {output_path}", err=True)
        else:
            try:
                click.echo(output_text)
            except UnicodeEncodeError:
                safe_text = output_text.encode('ascii', errors='replace').decode('ascii')
                click.echo(safe_text)
        
    except PreApplyError as e:
        click.echo(format_error(str(e)), err=True)
        sys.exit(1)
    except json.JSONDecodeError as e:
        error_msg = f"The file {plan_json} is not valid JSON. Please ensure it's a valid Terraform plan JSON file."
        click.echo(format_error(error_msg), err=True)
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        click.echo(format_error(f"Analysis failed: {e}"), err=True)
        sys.exit(1)


def _format_json_output(output: CoreOutput) -> str:
    """Format CoreOutput as JSON string."""
    return json.dumps(output.model_dump(), indent=2)

