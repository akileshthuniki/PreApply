"""AI runtime management commands."""

import click
from ...config.manager import load_config, get_ai_config
from ...config.paths import get_user_config_path, get_project_config_path
from ...runtime.detector import detect_runtime
from ...runtime.models import list_available_models, validate_model
from ...runtime.registry import SUPPORTED_RUNTIMES
from ...utils.logging import get_logger

logger = get_logger("cli.ai")


@click.group()
def ai():
    """AI runtime management."""
    pass


@ai.command()
def status():
    """Show AI configuration status."""
    config = load_config()
    ai_config = get_ai_config(config)
    
    # Determine state
    user_config_path = get_user_config_path()
    project_config_path = get_project_config_path()
    
    if not user_config_path.exists() and not project_config_path:
        # Not configured
        click.echo("AI Status: Not configured")
        click.echo("Run: preapply setup ai")
        return
    
    if not ai_config.get("enabled", False):
        # Configured but disabled
        click.echo("AI Status: Configured but disabled")
        runtime = ai_config.get("runtime", "unknown")
        model = ai_config.get("model", "unknown")
        click.echo(f"Runtime: {runtime}")
        click.echo(f"Model: {model}")
        click.echo("Enable with: preapply setup ai")
        return
    
    # Enabled - check runtime availability
    runtime_name = ai_config.get("runtime", "ollama")
    model = ai_config.get("model", "unknown")
    base_url = ai_config.get("base_url", "http://localhost:11434")
    
    detection = detect_runtime(runtime_name)
    
    if detection["available"]:
        # Enabled and healthy
        version = detection.get("version", "unknown")
        click.echo("AI Status: Enabled and healthy")
        click.echo(f"Runtime: {runtime_name} ({version})")
        click.echo(f"Model: {model}")
        click.echo(f"Base URL: {base_url}")
    else:
        # Enabled but runtime unavailable
        click.echo("AI Status: Enabled but runtime unavailable")
        click.echo(f"Runtime: {runtime_name}")
        click.echo(f"Model: {model}")
        
        if not detection["binary_found"]:
            click.echo(f"Error: {runtime_name} binary not found")
        elif not detection["service_reachable"]:
            click.echo(f"Error: {runtime_name} service not reachable at {base_url}")
        else:
            click.echo(f"Error: {runtime_name} is not available")


@ai.command()
def list():
    """List available models (read-only, never auto-start)."""
    config = load_config()
    ai_config = get_ai_config(config)
    runtime_name = ai_config.get("runtime", "ollama")
    
    try:
        click.echo(f"Querying {runtime_name} for available models...")
        models = list_available_models(runtime_name)
        
        if not models:
            click.echo("No models found.")
            return
        
        click.echo("")
        click.echo("Available models:")
        for model in models:
            click.echo(f"  - {model}")
        
        # Show current model if configured
        current_model = ai_config.get("model")
        if current_model:
            if current_model in models:
                click.echo("")
                click.echo(f"Current model: {current_model} ✓")
            else:
                click.echo("")
                click.echo(f"Current model: {current_model} (not in list)")
    except Exception as e:
        click.echo(f"Error: {e}")
        click.echo("")
        click.echo("Make sure Ollama is running:")
        click.echo("  ollama serve")


@ai.command()
@click.argument('model')
def use(model):
    """Switch to a different model."""
    config = load_config()
    ai_config = get_ai_config(config)
    
    if not ai_config.get("enabled", False):
        click.echo("AI is not enabled. Run: preapply setup ai")
        return
    
    runtime_name = ai_config.get("runtime", "ollama")
    
    # Validate model exists
    try:
        if not validate_model(model, runtime_name):
            click.echo(f"Model '{model}' not found locally.")
            if click.confirm(f"Pull model '{model}' now?", default=False):
                from ...runtime.models import pull_model
                if pull_model(model, runtime_name):
                    click.echo(f"✓ Successfully pulled model '{model}'")
                else:
                    click.echo(f"❌ Failed to pull model '{model}'")
                    return
            else:
                click.echo("Model not available. Please pull it first:")
                click.echo(f"  ollama pull {model}")
                return
    except Exception as e:
        click.echo(f"Error checking model: {e}")
        click.echo("Make sure Ollama is running.")
        return
    
    # Update config
    ai_config["model"] = model
    config["ai"] = ai_config
    
    from ...config.manager import save_config
    save_config(config)
    
    click.echo(f"✓ Switched to model: {model}")

