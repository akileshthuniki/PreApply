"""Policy loader - load and validate policy definitions from YAML."""

import yaml
from pathlib import Path
from typing import List, Dict, Any
from pydantic import ValidationError
from ..utils.errors import PreApplyError
from ..utils.logging import get_logger
from .models import Policy, MatchRule, Action

logger = get_logger("policy.loader")


def load_policies(policy_file: str) -> List[Policy]:
    """
    Load policies from YAML file.
    
    Args:
        policy_file: Path to policy YAML file
        
    Returns:
        List of Policy objects
        
    Raises:
        PreApplyError: If policy file is invalid
    """
    policy_path = Path(policy_file)
    
    if not policy_path.exists():
        raise PreApplyError(f"Policy file not found: {policy_file}")
    
    if not policy_path.is_file():
        raise PreApplyError(f"Path is not a file: {policy_file}")
    
    try:
        with open(policy_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise PreApplyError(f"Invalid YAML in policy file: {e}")
    except Exception as e:
        raise PreApplyError(f"Error reading policy file: {e}")
    
    if not isinstance(data, dict):
        raise PreApplyError("Policy file must contain a dictionary")
    
    if "policies" not in data:
        raise PreApplyError("Policy file must contain 'policies' key")
    
    policies_data = data["policies"]
    if not isinstance(policies_data, list):
        raise PreApplyError("'policies' must be a list")
    
    policies = []
    for idx, policy_data in enumerate(policies_data):
        try:
            policy = Policy(**policy_data)
            policies.append(policy)
        except ValidationError as e:
            raise PreApplyError(f"Invalid policy at index {idx}: {e}")
        except Exception as e:
            raise PreApplyError(f"Error parsing policy at index {idx}: {e}")
    
    if not policies:
        raise PreApplyError("No valid policies found in policy file")
    
    logger.info(f"Loaded {len(policies)} policies from {policy_file}")
    return policies


def validate_policy_file(policy_file: str) -> bool:
    """
    Validate policy file without loading policies.
    
    Args:
        policy_file: Path to policy YAML file
        
    Returns:
        True if valid
        
    Raises:
        PreApplyError: If policy file is invalid
    """
    try:
        load_policies(policy_file)
        return True
    except PreApplyError:
        raise
    except Exception as e:
        raise PreApplyError(f"Policy validation failed: {e}")

