"""Configuration module: Load and access scoring weights and thresholds."""

from pathlib import Path
import yaml
from typing import Dict, Any
from ..utils.errors import ConfigError
from ..utils.logging import get_logger
from .manager import load_config, get_ai_config, save_config
from .paths import get_config_path, get_user_config_path, get_project_config_path

logger = get_logger("config")


def load_scoring_config(config_path: str = None) -> Dict[str, Any]:
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Path to config YAML file. If None, uses defaults.yaml
        
    Returns:
        Configuration dictionary
        
    Raises:
        ConfigError: If config cannot be loaded
    """
    if config_path is None:
        # Use default config file
        config_path = Path(__file__).parent / "defaults.yaml"
    else:
        config_path = Path(config_path)
    
    if not config_path.exists():
        raise ConfigError(f"Config file not found: {config_path}")
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        if not isinstance(config, dict):
            raise ConfigError("Config file must contain a dictionary")
        
        # Validate required sections
        required_sections = ["blast_radius", "risk_levels", "shared_resources"]
        missing_sections = [s for s in required_sections if s not in config]
        
        # Validate nested structures
        validation_issues = []
        
        # Check blast_radius section
        if "blast_radius" in config:
            br_config = config["blast_radius"]
            if not isinstance(br_config, dict):
                validation_issues.append("blast_radius is not a dict")
            else:
                required_weights = ["shared_resource_weight", "downstream_service_weight", "delete_action_multiplier", "update_action_multiplier", "create_action_multiplier"]
                missing_weights = [w for w in required_weights if w not in br_config]
                if missing_weights:
                    validation_issues.append(f"blast_radius missing: {missing_weights}")
        
        # Check risk_levels section
        if "risk_levels" in config:
            rl_config = config["risk_levels"]
            if not isinstance(rl_config, dict):
                validation_issues.append("risk_levels is not a dict")
            else:
                required_levels = ["low", "medium", "high"]
                missing_levels = [l for l in required_levels if l not in rl_config]
                if missing_levels:
                    validation_issues.append(f"risk_levels missing: {missing_levels}")
        
        # Check shared_resources section
        if "shared_resources" in config:
            sr_config = config["shared_resources"]
            if not isinstance(sr_config, dict):
                validation_issues.append("shared_resources is not a dict")
            else:
                if "critical_types" not in sr_config:
                    validation_issues.append("shared_resources missing critical_types")
                elif not isinstance(sr_config["critical_types"], list):
                    validation_issues.append("critical_types is not a list")
        
        logger.info(f"Loaded configuration from {config_path}")
        return config
        
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML in config file: {e}")
    except Exception as e:
        raise ConfigError(f"Error loading config file: {e}")

