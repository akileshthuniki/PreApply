"""Summary command - generate short paragraph summary."""

import json
import click
import sys
from ...contracts.core_output import CoreOutput
from ...presentation.explainer import generate_summary_with_id
from ...utils.errors import PreApplyError
from ...utils.logging import get_logger
from ..utils import run_analysis, format_error

logger = get_logger("cli.summary")


@click.command()
@click.argument('plan_json', type=click.Path(exists=False))
@click.option('--json', is_flag=True, help='Output structured JSON')
@click.option('--quiet', is_flag=True, help='Suppress progress messages')
@click.option('--from-json', type=click.Path(exists=True), help='Reuse analysis from JSON file instead of running analysis')
def summary(plan_json, json, quiet, from_json):
    """Generate short paragraph summary of risk assessment."""
    try:
        # Load analysis result
        if from_json:
            with open(from_json, 'r', encoding='utf-8') as f:
                output_data = json.load(f)
            output = CoreOutput(**output_data)
            if not quiet:
                click.echo(f"Loaded analysis from: {from_json}", err=True)
        else:
            if not quiet:
                click.echo(f"Analyzing plan: {plan_json}", err=True)
            output = run_analysis(plan_json)
        
        # Generate summary
        summary_text, explanation_id = generate_summary_with_id(output)
        
        # Output
        if json:
            output_data = {
                "summary": summary_text,
                "explanation_id": explanation_id.value if hasattr(explanation_id, 'value') else str(explanation_id),
                "risk_level": output.risk_level.value,
                "blast_radius_score": output.blast_radius_score
            }
            click.echo(json.dumps(output_data, indent=2))
        else:
            if not quiet:
                click.echo("PreApply Summary")
                click.echo("-" * 60)
                click.echo("")
            try:
                click.echo(summary_text)
            except UnicodeEncodeError:
                safe_text = summary_text.encode('ascii', errors='replace').decode('ascii')
                click.echo(safe_text)
        
    except PreApplyError as e:
        click.echo(format_error(str(e)), err=True)
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        click.echo(format_error(f"Summary generation failed: {e}"), err=True)
        sys.exit(1)

