"""Explain command - generate deterministic explanations."""

import json
import click
import sys
from ...contracts.core_output import CoreOutput
from ...presentation.explainer import explain_overall_with_id, explain_resource_with_id, list_resources as list_available_resources
from ...utils.errors import PreApplyError
from ...utils.logging import get_logger
from ..utils import run_analysis, validate_resource_id, format_error

logger = get_logger("cli.explain")


def _is_core_output(data: dict) -> bool:
    """Check if JSON data is a PreApply CoreOutput."""
    return (
        isinstance(data, dict) and
        "version" in data and
        "risk_level" in data and
        "blast_radius_score" in data and
        "format_version" not in data  # Terraform plans have format_version
    )


@click.command()
@click.argument('input_file', type=click.Path(exists=False))
@click.argument('resource_id', required=False)
@click.option('--json', 'output_json', is_flag=True, help='Output structured JSON')
@click.option('--list-resources', is_flag=True, help='List all available resource IDs')
@click.option('--quiet', is_flag=True, help='Suppress progress messages')
@click.option('--from-json', type=click.Path(exists=True), help='Reuse analysis from JSON file instead of running analysis')
def explain(input_file, resource_id, output_json, list_resources, quiet, from_json):
    """
    Explain risk assessment or specific resource (deterministic, no AI).
    
    Accepts either:
    - Terraform plan JSON file (will analyze first)
    - PreApply analysis JSON file (CoreOutput format)
    
    Examples:
        preapply explain plan.json              # Analyze and explain Terraform plan
        preapply explain analysis.json          # Explain existing analysis
        preapply explain analysis.json aws_vpc.main  # Explain specific resource
    """
    try:
        # Load analysis result
        if from_json:
            with open(from_json, 'r', encoding='utf-8') as f:
                output_data = json.load(f)
            output = CoreOutput(**output_data)
            if not quiet:
                click.echo(f"Loaded analysis from: {from_json}", err=True)
        else:
            # Auto-detect if input is CoreOutput or Terraform plan
            try:
                with open(input_file, 'r', encoding='utf-8') as f:
                    file_data = json.load(f)
                
                if _is_core_output(file_data):
                    # It's a PreApply analysis JSON
                    output = CoreOutput(**file_data)
                    if not quiet:
                        click.echo(f"Loaded analysis from: {input_file}", err=True)
                else:
                    # It's a Terraform plan, analyze it
                    if not quiet:
                        click.echo(f"Analyzing Terraform plan: {input_file}", err=True)
                    output = run_analysis(input_file)
            except json.JSONDecodeError as e:
                raise PreApplyError(f"Invalid JSON file: {input_file}. {e}")
            except FileNotFoundError:
                raise PreApplyError(f"File not found: {input_file}")
        
        # Handle list-resources flag
        if list_resources:
            resources = list_available_resources(output)
            if resources:
                click.echo("Available resources for explanation:")
                for resource in resources:
                    click.echo(f"  - {resource}")
            else:
                click.echo("No resources found in analysis.")
            return
        
        # Generate explanation
        if resource_id:
            is_valid, error_msg, resource_data = validate_resource_id(output, resource_id)
            if not is_valid:
                click.echo(format_error(error_msg), err=True)
                sys.exit(1)
            
            explanation, explanation_id = explain_resource_with_id(output, resource_id)
        else:
            explanation, explanation_id = explain_overall_with_id(output)
        
        # Output
        if output_json:
            output_data = {
                "explanation": explanation,
                "explanation_id": explanation_id.value if hasattr(explanation_id, 'value') else str(explanation_id),
                "resource_id": resource_id,
                "risk_level": str(output.risk_level),
                "blast_radius_score": output.blast_radius_score
            }
            click.echo(json.dumps(output_data, indent=2))
        else:
            if not quiet:
                click.echo("PreApply Explanation")
                click.echo("-" * 60)
                click.echo("")
                sys.stdout.flush()
            try:
                click.echo(explanation)
                sys.stdout.flush()
            except UnicodeEncodeError:
                safe_text = explanation.encode('ascii', errors='replace').decode('ascii')
                click.echo(safe_text)
                sys.stdout.flush()
        
    except PreApplyError as e:
        click.echo(format_error(str(e)), err=True)
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        click.echo(format_error(f"Explanation failed: {e}"), err=True)
        sys.exit(1)
