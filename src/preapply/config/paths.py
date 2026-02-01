"""Config path resolution for two-tier config system."""

from pathlib import Path
from typing import Optional

def get_user_config_path() -> Path:
    """Get user config path: ~/.preapply/config.yaml"""
    home = Path.home()
    return home / ".preapply" / "config.yaml"


def get_project_config_path() -> Optional[Path]:
    """Get project config path: .preapply/config.yaml (from current working directory)"""
    cwd = Path.cwd()
    project_config = cwd / ".preapply" / "config.yaml"
    if project_config.exists():
        return project_config
    return None


def get_config_path() -> Path:
    """
    Resolve config location (project first, then user).
    
    Returns:
        Path to config file (project if exists, otherwise user)
    """
    project_config = get_project_config_path()
    if project_config:
        return project_config
    return get_user_config_path()

