"""Two-tier configuration manager (user + project override)."""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from .paths import get_user_config_path, get_project_config_path, get_config_path
from ..utils.errors import ConfigError
from ..utils.logging import get_logger

logger = get_logger("config.manager")


def load_config() -> Dict[str, Any]:
    """
    Load full config tree with project override.
    
    Returns:
        Configuration dictionary (project config overrides user config)
    """
    user_config_path = get_user_config_path()
    project_config_path = get_project_config_path()
    
    # Start with user config
    config = {}
    if user_config_path.exists():
        try:
            with open(user_config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning(f"Could not load user config from {user_config_path}: {e}")
    
    # Override with project config if it exists
    if project_config_path:
        try:
            with open(project_config_path, 'r', encoding='utf-8') as f:
                project_config = yaml.safe_load(f) or {}
                # Deep merge (simple version - project overrides user)
                _deep_merge(config, project_config)
                logger.info(f"Loaded project config from {project_config_path}")
        except Exception as e:
            logger.warning(f"Could not load project config from {project_config_path}: {e}")
    
    return config


def get_ai_config(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Return AI subsection from loaded config.
    
    Args:
        config: Optional config dict (if None, loads from file)
        
    Returns:
        AI configuration dictionary
    """
    if config is None:
        config = load_config()
    
    return config.get("ai", {})


def save_config(config: Dict[str, Any], path: Optional[Path] = None) -> None:
    """
    Save config to specified path (defaults to user config).
    
    Args:
        config: Configuration dictionary to save
        path: Optional path to save to (defaults to user config)
    """
    if path is None:
        path = get_user_config_path()
    
    # Ensure directory exists
    path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        logger.info(f"Saved config to {path}")
    except Exception as e:
        raise ConfigError(f"Failed to save config to {path}: {e}")


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> None:
    """Deep merge override into base (mutates base)."""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value

