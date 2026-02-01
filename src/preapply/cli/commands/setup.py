"""Setup command for PreApply components."""

import click
from ...config.manager import load_config, get_ai_config, save_config
from ...config.paths import get_user_config_path
from ...runtime.detector import detect_runtime
from ...runtime.models import pull_model, validate_model
from ...runtime.registry import SUPPORTED_RUNTIMES
from ...utils.logging import get_logger

logger = get_logger("cli.setup")


@click.group()
def setup():
    """Setup PreApply components."""
    pass


@setup.command()
def ai():
    """Setup AI runtime."""
    _setup_ai()


def _setup_ai():
    """Interactive AI setup flow."""
    # Dry explanation mode (before consent)
    click.echo("PreApply AI Setup")
    click.echo("─────────────────")
    click.echo("")
    click.echo("AI will:")
    click.echo("- Use Ollama running locally")
    click.echo("- Pull a model (~4-8GB)")
    click.echo("- Store config in ~/.preapply/config.yaml")
    click.echo("")
    click.echo("AI will NOT:")
    click.echo("- Send data externally")
    click.echo("- Modify analysis results")
    click.echo("- Run automatically")
    click.echo("")
    
    if not click.confirm("Proceed?", default=False):
        click.echo("Setup cancelled.")
        return
    
    # Runtime detection
    click.echo("")
    click.echo("Detecting Ollama runtime...")
    detection = detect_runtime("ollama")
    
    if not detection["binary_found"]:
        click.echo("")
        click.echo("❌ Ollama binary not found.")
        click.echo("")
        click.echo("Please install Ollama:")
        click.echo("  https://ollama.ai")
        click.echo("")
        click.echo("After installation, run: preapply setup ai")
        return
    
    if not detection["service_reachable"]:
        click.echo("")
        click.echo("❌ Ollama service not reachable.")
        click.echo("")
        click.echo("Please start Ollama:")
        click.echo("  ollama serve")
        click.echo("")
        click.echo("Then run: preapply setup ai")
        return
    
    click.echo(f"✓ Ollama detected (version: {detection.get('version', 'unknown')})")
    
    # Model selection
    click.echo("")
    click.echo("Select default model:")
    registry = SUPPORTED_RUNTIMES["ollama"]
    models = registry["default_models"]
    model_sizes = registry["model_sizes"]
    
    for i, model in enumerate(models, 1):
        size = model_sizes.get(model, "unknown size")
        click.echo(f"  {i}. {model} ({size})")
    
    click.echo(f"  {len(models) + 1}. Custom")
    
    choice = click.prompt("Enter choice", type=int, default=1)
    
    if choice <= len(models):
        selected_model = models[choice - 1]
    else:
        selected_model = click.prompt("Enter model name", type=str)
    
    # Model pull
    click.echo("")
    click.echo(f"Checking if model '{selected_model}' is available...")
    
    if not validate_model(selected_model):
        click.echo(f"Model '{selected_model}' not found locally.")
        if click.confirm(f"Pull model '{selected_model}' now?", default=True):
            click.echo(f"Pulling model '{selected_model}' (this may take a while)...")
            if pull_model(selected_model):
                click.echo(f"✓ Successfully pulled model '{selected_model}'")
            else:
                click.echo(f"❌ Failed to pull model '{selected_model}'")
                click.echo("")
                click.echo("You can pull it manually:")
                click.echo(f"  ollama pull {selected_model}")
                click.echo("")
                click.echo("Then run: preapply setup ai")
                return
        else:
            click.echo("")
            click.echo("Please pull the model manually:")
            click.echo(f"  ollama pull {selected_model}")
            click.echo("")
            click.echo("Then run: preapply setup ai")
            return
    else:
        click.echo(f"✓ Model '{selected_model}' is available")
    
    # Config persistence
    config = load_config()
    config.setdefault("ai", {})
    config["ai"]["enabled"] = True
    config["ai"]["runtime"] = "ollama"
    config["ai"]["model"] = selected_model
    config["ai"]["base_url"] = registry["api_base"]
    
    save_config(config)
    
    click.echo("")
    click.echo("✓ AI setup complete!")
    click.echo("")
    click.echo("You can now use:")
    click.echo("  preapply ask ai \"Your question\" analysis.json")
    click.echo("  preapply ai status")

