"""Load and validate Terraform plan JSON."""

import json
from pathlib import Path
from typing import Dict, Any
from ..utils.errors import PlanLoadError
from ..utils.logging import get_logger

try:
    from .plan_validator import validate_plan_structure, get_plan_summary
except Exception as e:
    raise

logger = get_logger("ingest.plan_loader")


def load_plan_json(plan_path: str) -> Dict[str, Any]:
    """
    Load and validate Terraform plan JSON file.
    
    Args:
        plan_path: Path to Terraform plan JSON file
        
    Returns:
        Parsed and validated plan data
        
    Raises:
        PlanLoadError: If file cannot be loaded or is invalid
    """
    path = Path(plan_path)
    
    if not path.exists():
        raise PlanLoadError(
            f"Plan file not found: {plan_path}. "
            "Please check the file path and ensure the file exists. "
            "Generate a plan using: terraform plan -json > plan.json"
        )
    
    if not path.is_file():
        raise PlanLoadError(
            f"Path is not a file: {plan_path}. "
            "Please provide a valid Terraform plan JSON file."
        )
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            plan_data = json.load(f)
    except json.JSONDecodeError as e:
        raise PlanLoadError(
            f"Invalid JSON in plan file: {e}. "
            "Please ensure the file is valid JSON. "
            "Generate a plan using: terraform plan -json > plan.json"
        )
    except Exception as e:
        raise PlanLoadError(
            f"Error reading plan file: {e}. "
            "Please check file permissions and try again."
        )
    
    # Validate plan structure
    try:
        validate_plan_structure(plan_data)
    except PlanLoadError as e:
        # Re-raise with helpful context
        raise PlanLoadError(
            f"Invalid Terraform plan structure: {e}. "
            "Please ensure you're using a valid Terraform plan JSON file. "
            "Generate one using: terraform plan -json > plan.json"
        )
    
    # Ensure resource_changes exists (even if empty)
    if "resource_changes" not in plan_data:
        logger.warning("Plan JSON missing 'resource_changes' field - may be empty plan")
        plan_data["resource_changes"] = []
    
    # Log plan summary
    summary = get_plan_summary(plan_data)
    logger.info(
        f"Loaded Terraform plan from {plan_path} "
        f"(version: {summary['terraform_version']}, "
        f"resources: {summary['resource_count']})"
    )
    
    return plan_data

