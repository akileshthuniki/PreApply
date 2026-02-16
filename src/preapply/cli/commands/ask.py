"""Ask command - AI advisor for CoreOutput (read-only, advisory only)."""

import json
import click
from pathlib import Path
from typing import Optional
from ...contracts.core_output import CoreOutput
from ...utils.errors import PreApplyError
from ...utils.logging import get_logger
from ..utils import format_error, run_analysis
from ..utils.file_resolver import resolve_file_path

logger = get_logger("cli.ask")


def _is_terraform_plan(data: dict) -> bool:
    """True if JSON looks like a Terraform plan."""
    return "resource_changes" in data or "terraform_version" in data


def _is_core_output(data: dict) -> bool:
    """True if JSON looks like PreApply CoreOutput."""
    return "risk_level" in data and "blast_radius_score" in data and "risk_attributes" in data


def _load_output_from_file(file_path: str) -> CoreOutput:
    """
    Load CoreOutput from file. Accepts either Terraform plan (runs analysis)
    or PreApply analysis JSON (CoreOutput).
    """
    path = resolve_file_path(file_path)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if _is_core_output(data):
        return CoreOutput(**data)
    if _is_terraform_plan(data):
        click.echo("Detected Terraform plan - running analysis first...", err=True)
        return run_analysis(str(path))
    raise ValueError(
        "File is neither a Terraform plan nor a PreApply analysis. "
        "Use a plan from 'terraform plan -out=tfplan' (then terraform show -json tfplan > plan.json) "
        "or run 'preapply analyze plan.json --json -o analysis.json' first."
    )


def _check_ai_installed() -> bool:
    """
    Check if AI support is installed.
    
    Returns:
        True if AI dependencies are available, False otherwise
    """
    try:
        from ...ai.ollama import OllamaAdvisor
        return True
    except ImportError:
        return False


def _get_ollama_advisor(model: Optional[str] = None):
    """
    Get Ollama advisor instance.
    
    Args:
        model: Optional model name (default: llama3.2)
        
    Returns:
        OllamaAdvisor instance
        
    Raises:
        PreApplyError: If AI is not installed or Ollama is not available
    """
    # Check if AI is installed
    if not _check_ai_installed():
        raise PreApplyError(
            "AI support is not installed. Install it with: pip install 'preapply[ai]'"
        )
    
    try:
        from ...ai.ollama import OllamaAdvisor
        return OllamaAdvisor(model=model or "llama3.2")
    except PreApplyError as e:
        # Ollama not running or not available
        error_msg = str(e)
        if "not available" in error_msg.lower():
            raise PreApplyError(
                "Ollama is not running. Please start Ollama and try again. "
                "Visit https://ollama.ai for installation instructions."
            )
        raise
    except Exception as e:
        raise PreApplyError(f"Failed to initialize Ollama advisor: {e}")


@click.command()
@click.argument('provider_keyword', type=str)
@click.argument('question', type=str)
@click.argument('file_path', type=click.Path(exists=False))
@click.option('--model', default='llama3.2', help='Ollama model name (default: llama3.2)')
@click.option('--max-tokens', type=int, help='Maximum tokens for response')
@click.option('--json', 'output_json', is_flag=True, help='Output JSON format')
def ask(provider_keyword, question, file_path, model, max_tokens, output_json):
    """
    Ask AI advisor about PreApply analysis (read-only helper).
    
    IMPORTANT: AI is just a helper. It cannot:
    - Edit or modify anything
    - Change risk scores or levels
    - Affect policy decisions
    - Modify the plan or analysis
    
    AI only helps you understand what's inside the plan file and answers
    questions related to the analysis.
    
    Syntax: preapply ask ai "Question" file.json
    
    Examples:
        preapply ask ai "What is the worst case impact?" analysis.json
        preapply ask ai "How can I reduce risk?" analysis.json
        preapply ask ai "Explain the blast radius" analysis.json --model llama3.1
    """
    try:
        # Validate provider keyword
        if provider_keyword.lower() != 'ai':
            click.echo(format_error(
                f"Invalid provider keyword: {provider_keyword}. Use 'ai' to enable AI advisor."
            ), err=True)
            click.get_current_context().exit(1)
        
        # Load CoreOutput (from analysis JSON or Terraform plan)
        try:
            output_obj = _load_output_from_file(file_path)
        except FileNotFoundError as e:
            error_msg = (
                f"{e}\n\nYou can use either:\n"
                "  • A Terraform plan: preapply ask ai \"Your question\" plan.json\n"
                "  • Or save analysis first: preapply analyze plan.json --json -o analysis.json"
            )
            click.echo(format_error(error_msg), err=True)
            click.get_current_context().exit(1)
        except json.JSONDecodeError as e:
            error_msg = f"The file {file_path} is not valid JSON."
            click.echo(format_error(error_msg), err=True)
            click.get_current_context().exit(1)
        except ValueError as e:
            click.echo(format_error(str(e)), err=True)
            click.get_current_context().exit(1)
        except PreApplyError as e:
            click.echo(format_error(str(e)), err=True)
            click.get_current_context().exit(1)
        
        # Get AI advisor
        try:
            advisor = _get_ollama_advisor(model)
        except PreApplyError as e:
            click.echo(format_error(str(e)), err=True)
            click.get_current_context().exit(1)
        
        # Check if advisor is available
        if not advisor.is_available():
            click.echo(format_error(
                "Ollama is not running. Please start Ollama and try again. "
                "Visit https://ollama.ai for installation instructions."
            ), err=True)
            click.get_current_context().exit(1)
        
        # Get AI response
        try:
            response = advisor.ask(output_obj, question, max_tokens=max_tokens)
        except PreApplyError as e:
            click.echo(format_error(str(e)), err=True)
            click.get_current_context().exit(1)
        
        # Output response (clearly labeled as ADVISORY)
        if output_json:
            result = {
                "advisory": True,
                "ai_enabled": True,
                "provider": "ollama",
                "model": model,
                "question": question,
                "response": response,
                "disclaimer": "AI is just a helper. It cannot edit, modify, or change anything. It only helps you understand what's inside the plan file."
            }
            click.echo(json.dumps(result, indent=2))
        else:
            click.echo("=" * 60)
            click.echo("AI ADVISOR (Read-Only Helper)")
            click.echo("=" * 60)
            click.echo(f"\nQuestion: {question}\n")
            click.echo(f"Response:\n{response}\n")
            click.echo("-" * 60)
            click.echo("NOTE: AI is just a helper. It cannot edit, modify, or change anything.")
            click.echo("It only helps you understand what's inside the plan file.")
            click.echo("=" * 60)
    
    except PreApplyError as e:
        click.echo(format_error(str(e)), err=True)
        click.get_current_context().exit(1)
    except click.exceptions.Exit:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        click.echo(format_error(f"Failed to get AI response: {e}"), err=True)
        click.get_current_context().exit(1)
