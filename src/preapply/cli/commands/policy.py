"""Policy command - check policies against analysis."""

import click
import sys
import json
from ...contracts.core_output import CoreOutput
from ...presentation.explainer import explain_overall_with_id, explain_resource_with_id
from ...policy.engine import check_policies
from ...utils.errors import PreApplyError
from ...utils.logging import get_logger
from ...config.environment import load_environment_config, get_enforcement_mode
from ..utils import run_analysis, format_error

logger = get_logger("cli.policy")


@click.group()
def policy():
    """Policy enforcement commands."""
    pass


@policy.command()
@click.argument('plan_json', type=click.Path(exists=False), required=False)
@click.option('--policy-file', '-p', type=click.Path(exists=True), required=True, help='Path to policy YAML file')
@click.option('--resource-id', help='Check policy for specific resource')
@click.option('--json', 'json_output', is_flag=True, help='Output structured JSON')
@click.option('--quiet', is_flag=True, help='Suppress progress messages')
@click.option('--from-json', type=click.Path(exists=True), help='Reuse analysis from JSON file instead of running analysis')
@click.option('--environment', type=click.Path(exists=True), help='Path to environment config file (.preapply-env.yaml)')
@click.option('--enforcement-mode', type=click.Choice(['auto', 'manual']), help='Override enforcement mode (auto=block, manual=require approval)')
def check(plan_json, policy_file, resource_id, json_output, quiet, from_json, environment, enforcement_mode):
    """Check policies against Terraform plan analysis."""
    try:
        # Load environment configuration
        env_config = load_environment_config(env_config_path=environment)
        effective_mode = get_enforcement_mode(env_config, enforcement_mode)
        
        if not quiet and env_config:
            click.echo(f"Environment: {env_config.name} (enforcement: {effective_mode})", err=True)
        
        # Load analysis result
        if from_json:
            with open(from_json, 'r', encoding='utf-8') as f:
                output_data = json.load(f)
            output = CoreOutput(**output_data)
            if not quiet:
                click.echo(f"Loaded analysis from: {from_json}", err=True)
        else:
            if not plan_json:
                click.echo(format_error("Either plan_json argument or --from-json option is required"), err=True)
                sys.exit(1)
            if not quiet:
                click.echo(f"Analyzing plan: {plan_json}", err=True)
            # Run analysis using shared helper
            output = run_analysis(plan_json)
        
        # Get explanation ID
        if resource_id:
            explanation_id = explain_resource_with_id(output, resource_id)[1]
        else:
            explanation_id = explain_overall_with_id(output)[1]
        
        # Check policies
        if not quiet:
            click.echo(f"Checking policies from: {policy_file}", err=True)
        
        result = check_policies(output, explanation_id, policy_file, resource_id)
        
        # Output results
        if json_output:
            output_data = {
                "passed": result.passed,
                "failure_count": result.failure_count,
                "warning_count": result.warning_count,
                "results": [
                    {
                        "policy_id": r.policy_id,
                        "matched": r.matched,
                        "action": r.action.value if hasattr(r.action, 'value') else str(r.action),
                        "explanation": r.explanation
                    }
                    for r in result.results
                ]
            }
            click.echo(json.dumps(output_data, indent=2))
        else:
            # Human-readable output
            if not quiet:
                click.echo("PreApply Policy Check")
                click.echo("-" * 60)  # ASCII for compatibility
                click.echo("")
            
            # Show matched policies
            matched = [r for r in result.results if r.matched]
            if matched:
                for r in matched:
                    # Use ASCII symbols for compatibility
                    action_symbol = "[FAIL]" if r.action.value == "fail" else "[WARN]" if r.action.value == "warn" else "[PASS]"
                    try:
                        click.echo(f"{action_symbol} {r.explanation}")
                    except UnicodeEncodeError:
                        safe_text = f"{action_symbol} {r.explanation}".encode('ascii', errors='replace').decode('ascii')
                        click.echo(safe_text)
                
                click.echo("")
                sys.stdout.flush()
            
            # Show summary
            try:
                if result.passed:
                    click.echo("[PASS] Policy check PASSED")
                else:
                    click.echo("[FAIL] Policy check FAILED")
                    click.echo(f"  {result.failure_count} policy violation(s) found")
            except UnicodeEncodeError:
                if result.passed:
                    click.echo("[PASS] Policy check PASSED")
                else:
                    click.echo("[FAIL] Policy check FAILED")
                    click.echo(f"  {result.failure_count} policy violation(s) found")
            sys.stdout.flush()
        
        # Exit with appropriate code based on enforcement mode
        # 0 = success (passed)
        # 1 = runtime error (handled by exception handler)
        # 2 = policy violation (auto-block)
        # 3 = policy violation (manual approval required)
        if result.passed:
            sys.exit(0)
        else:
            # Determine exit code based on enforcement mode
            if effective_mode == "auto":
                sys.exit(2)  # Hard block - CI will fail
            else:  # manual
                sys.exit(3)  # Needs approval - CI will pause
        
    except PreApplyError as e:
        click.echo(format_error(str(e)), err=True)
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        click.echo(format_error(f"Policy check failed: {e}"), err=True)
        sys.exit(1)

