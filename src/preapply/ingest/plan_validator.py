"""Validate Terraform plan JSON structure."""

from typing import Dict, Any, List, Optional
from ..utils.errors import PlanLoadError
from ..utils.logging import get_logger

logger = get_logger("ingest.plan_validator")


def validate_plan_structure(plan_data: Dict[str, Any]) -> None:
    """
    Validate Terraform plan JSON structure.
    
    Args:
        plan_data: Parsed Terraform plan JSON
        
    Raises:
        PlanLoadError: If plan structure is invalid
    """
    if not isinstance(plan_data, dict):
        raise PlanLoadError(
            "Plan JSON must be a dictionary. "
            "Please ensure you're using a valid Terraform plan JSON file."
        )
    
    # Check for required top-level fields
    required_fields = ["format_version"]
    missing_fields = [field for field in required_fields if field not in plan_data]
    
    if missing_fields:
        raise PlanLoadError(
            f"Plan JSON missing required fields: {', '.join(missing_fields)}. "
            "This doesn't appear to be a valid Terraform plan JSON file. "
            "Generate one using: terraform plan -json > plan.json"
        )
    
    # Validate format_version
    format_version = plan_data.get("format_version")
    if format_version:
        if not isinstance(format_version, str):
            raise PlanLoadError(
                "Plan 'format_version' must be a string. "
                "This may not be a valid Terraform plan JSON file."
            )
        
        # Check for supported format versions
        supported_versions = ["1.0", "1.1", "1.2", "1.3", "1.4", "1.5"]
        version_major_minor = ".".join(format_version.split(".")[:2])
        if version_major_minor not in supported_versions:
            logger.warning(
                f"Plan format version '{format_version}' may not be fully supported. "
                f"Supported versions: {', '.join(supported_versions)}"
            )
    
    # Check for resource_changes (warn if missing, but allow empty plans)
    if "resource_changes" not in plan_data:
        logger.warning(
            "Plan JSON missing 'resource_changes' field. "
            "This may be an empty plan with no changes."
        )
    else:
        resource_changes = plan_data.get("resource_changes", [])
        if not isinstance(resource_changes, list):
            raise PlanLoadError(
                "Plan 'resource_changes' must be a list. "
                "This may not be a valid Terraform plan JSON file."
            )
    
    # Validate terraform_version if present
    terraform_version = plan_data.get("terraform_version")
    if terraform_version and not isinstance(terraform_version, str):
        raise PlanLoadError(
            "Plan 'terraform_version' must be a string. "
            "This may not be a valid Terraform plan JSON file."
        )
    
    logger.debug("Plan structure validation passed")


def validate_resource_change(resource: Dict[str, Any]) -> List[str]:
    """
    Validate a single resource change structure.
    
    Args:
        resource: Resource change dictionary
        
    Returns:
        List of validation warnings (empty if valid)
    """
    warnings = []
    
    if not isinstance(resource, dict):
        warnings.append("Resource change must be a dictionary")
        return warnings
    
    # Check for required fields
    required_fields = ["address", "mode", "type", "name", "change"]
    missing_fields = [field for field in required_fields if field not in resource]
    
    if missing_fields:
        warnings.append(f"Missing required fields: {', '.join(missing_fields)}")
    
    # Validate change structure
    change = resource.get("change", {})
    if isinstance(change, dict):
        if "actions" not in change:
            warnings.append("Resource change missing 'actions' field")
        else:
            actions = change.get("actions", [])
            if not isinstance(actions, list):
                warnings.append("Resource change 'actions' must be a list")
    
    return warnings


def get_plan_summary(plan_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract summary information from plan.
    
    Args:
        plan_data: Parsed Terraform plan JSON
        
    Returns:
        Dictionary with plan summary information
    """
    resource_changes = plan_data.get("resource_changes", [])
    
    summary = {
        "format_version": plan_data.get("format_version", "unknown"),
        "terraform_version": plan_data.get("terraform_version", "unknown"),
        "resource_count": len(resource_changes),
        "planned_values": plan_data.get("planned_values", {}),
    }
    
    # Count actions
    action_counts = {"create": 0, "update": 0, "delete": 0, "replace": 0, "no-op": 0}
    
    for resource in resource_changes:
        change = resource.get("change", {})
        actions = change.get("actions", [])
        
        for action in actions:
            if action in action_counts:
                action_counts[action] += 1
            elif action == "no-op":
                action_counts["no-op"] += 1
    
    summary["action_counts"] = action_counts
    
    return summary
