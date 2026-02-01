"""Environment configuration for CI/CD policy enforcement."""

from typing import Optional
from pathlib import Path
import yaml
from ..utils.logging import get_logger

logger = get_logger("config.environment")


class EnvironmentConfig:
    """Environment configuration for policy enforcement."""
    
    def __init__(self, name: str, enforcement_mode: str):
        """
        Initialize environment configuration.
        
        Args:
            name: Environment name (development, staging, preprod, production)
            enforcement_mode: Enforcement mode ("auto" or "manual")
        """
        self.name = name
        self.enforcement_mode = enforcement_mode
    
    def __repr__(self) -> str:
        return f"EnvironmentConfig(name={self.name}, enforcement_mode={self.enforcement_mode})"


def load_environment_config(env_config_path: Optional[str] = None) -> Optional[EnvironmentConfig]:
    """
    Load environment configuration from file or environment variable.
    
    Priority:
    1. Config file path (if provided)
    2. .preapply-env.yaml in current directory
    3. PREAPPLY_ENV environment variable
    4. Default to development/auto
    
    Args:
        env_config_path: Optional path to environment config file (.preapply-env.yaml)
        
    Returns:
        EnvironmentConfig or None if not found
    """
    import os
    
    # Try config file path first
    if env_config_path:
        config_file = Path(env_config_path)
        if config_file.exists():
            return _load_from_file(config_file)
    
    # Try .preapply-env.yaml in current directory
    current_dir = Path.cwd()
    config_file = current_dir / ".preapply-env.yaml"
    if config_file.exists():
        return _load_from_file(config_file)
    
    # Try parent directories (up to 3 levels)
    for parent in current_dir.parents[:3]:
        config_file = parent / ".preapply-env.yaml"
        if config_file.exists():
            return _load_from_file(config_file)
    
    # Try environment variable
    env_var = os.getenv("PREAPPLY_ENV")
    if env_var:
        # Format: "name:mode" or just "name" (defaults to auto)
        if ":" in env_var:
            name, mode = env_var.split(":", 1)
            name = name.strip().lower()
            mode = mode.strip().lower()
            # Validate mode
            if mode not in ["auto", "manual"]:
                logger.warning(f"Invalid enforcement_mode '{mode}' in PREAPPLY_ENV, defaulting to 'auto'")
                mode = "auto"
            return EnvironmentConfig(name=name, enforcement_mode=mode)
        else:
            # Default to auto mode if only name provided
            name = env_var.strip().lower()
            return EnvironmentConfig(name=name, enforcement_mode="auto")
    
    # Default: development with auto enforcement
    logger.debug("No environment config found, defaulting to development/auto")
    return EnvironmentConfig(name="development", enforcement_mode="auto")


def _load_from_file(config_file: Path) -> Optional[EnvironmentConfig]:
    """Load environment config from YAML file."""
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        if not data or "environment" not in data:
            logger.warning(f"Config file {config_file} missing 'environment' key")
            return None
        
        env_data = data["environment"]
        # Normalize values defensively (case-insensitive)
        name = env_data.get("name", "development").lower()
        enforcement_mode = env_data.get("enforcement_mode", "auto").lower()
        
        # Validate enforcement_mode
        if enforcement_mode not in ["auto", "manual"]:
            logger.warning(f"Invalid enforcement_mode '{enforcement_mode}', defaulting to 'auto'")
            enforcement_mode = "auto"
        
        logger.debug(f"Loaded environment config: {name} ({enforcement_mode})")
        return EnvironmentConfig(name=name, enforcement_mode=enforcement_mode)
    
    except yaml.YAMLError as e:
        logger.error(f"Failed to parse config file {config_file}: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to load config file {config_file}: {e}")
        return None


def get_enforcement_mode(
    env_config: Optional[EnvironmentConfig],
    override_mode: Optional[str] = None
) -> str:
    """
    Get enforcement mode with override support.
    
    Args:
        env_config: Environment configuration (from file/env var)
        override_mode: CLI flag override ("auto" or "manual")
        
    Returns:
        Enforcement mode: "auto" or "manual"
    """
    # CLI override takes precedence
    if override_mode:
        if override_mode not in ["auto", "manual"]:
            logger.warning(f"Invalid override mode '{override_mode}', ignoring")
        else:
            return override_mode
    
    # Use config if available
    if env_config:
        return env_config.enforcement_mode
    
    # Default to auto
    return "auto"

