"""CLI utilities package."""

import json
from pathlib import Path
from typing import Tuple, Optional, List
from ...utils.errors import PreApplyError
from ...utils.logging import get_logger
from .file_resolver import resolve_file_path

logger = get_logger("cli.utils")


def validate_plan_json(plan_path: str) -> Tuple[bool, Optional[str], Optional[dict]]:
    """
    Validate plan.json file exists and is valid JSON.
    
    Returns:
        Tuple of (is_valid, error_message, plan_data)
    """
    path = Path(plan_path)
    
    if not path.exists():
        return False, f"Plan file not found: {plan_path}", None
    
    if not path.is_file():
        return False, f"Path is not a file: {plan_path}", None
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            plan_data = json.load(f)
        return True, None, plan_data
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON in plan file: {e}", None
    except Exception as e:
        return False, f"Error reading plan file: {e}", None


def validate_resource_id(output, resource_id: str) -> Tuple[bool, Optional[str], Optional[dict]]:
    """
    Validate resource_id exists in analysis output.
    
    Returns:
        Tuple of (is_valid, error_message, resource_data)
    """
    attrs = output.risk_attributes
    
    # Check shared dependencies
    for dep in attrs.shared_dependencies:
        if dep.resource_id == resource_id or resource_id in dep.resource_id:
            return True, None, {
                "resource_id": dep.resource_id,
                "resource_type": dep.resource_type,
                "dependents": dep.dependents,
                "is_critical": dep.is_critical,
                "is_shared": True,
                "risk_reason": dep.risk_reason
            }
    
    # Check critical infrastructure
    for crit in attrs.critical_infrastructure:
        if crit.resource_id == resource_id or resource_id in crit.resource_id:
            return True, None, {
                "resource_id": crit.resource_id,
                "resource_type": crit.resource_type,
                "dependents": None,
                "is_critical": True,
                "is_shared": False,
                "risk_reason": crit.risk_reason
            }
    
    # Resource not found - suggest similar ones
    all_resources = []
    for dep in attrs.shared_dependencies:
        all_resources.append(dep.resource_id)
    for crit in attrs.critical_infrastructure:
        all_resources.append(crit.resource_id)
    
    suggestions = _find_similar_resources(resource_id, all_resources)
    
    error_msg = f"Resource '{resource_id}' not found in analysis."
    if suggestions:
        error_msg += f"\nSimilar resources: {', '.join(suggestions[:5])}"
    else:
        error_msg += f"\nAvailable resources: {', '.join(all_resources[:10])}"
    
    return False, error_msg, None


def _find_similar_resources(target: str, resources: List[str]) -> List[str]:
    """Find resources with similar names to target."""
    target_lower = target.lower()
    similar = []
    
    for resource in resources:
        resource_lower = resource.lower()
        if target_lower in resource_lower or resource_lower in target_lower:
            similar.append(resource)
        elif any(part in resource_lower for part in target_lower.split('.') if len(part) > 2):
            similar.append(resource)
    
    return similar[:5]


def format_error(message: str, suggestion: Optional[str] = None) -> str:
    """
    Format error message with optional suggestion.
    
    Args:
        message: Error message
        suggestion: Optional suggestion or help text
        
    Returns:
        Formatted error string
    """
    try:
        error = f"❌ Error: {message}"
        if suggestion:
            error += f"\n💡 Tip: {suggestion}"
        return error
    except Exception:
        # Fallback without emoji
        error = f"Error: {message}"
        if suggestion:
            error += f"\nTip: {suggestion}"
        return error


def run_analysis(plan_json: str) -> "CoreOutput":
    """
    Shared analysis execution helper - all commands call this.
    
    Args:
        plan_json: Path to Terraform plan JSON file
        
    Returns:
        CoreOutput object
        
    Raises:
        PreApplyError: If analysis fails
    """
    from ... import analyze as analyze_core
    
    # Validate plan.json first
    is_valid, error_msg, plan_data = validate_plan_json(plan_json)
    if not is_valid:
        raise PreApplyError(error_msg)
    
    # Check if plan has changes
    if plan_data and "resource_changes" in plan_data:
        if len(plan_data["resource_changes"]) == 0:
            # Empty plan
            output_dict = handle_empty_plan()
            from ...contracts.core_output import CoreOutput as CO
            return CO(**output_dict)
    
    # Run analysis
    result = analyze_core(plan_json)
    
    # Convert to CoreOutput
    from ...contracts.core_output import CoreOutput as CO
    if isinstance(result, dict) and "structured" in result:
        return CO(**result["structured"])
    elif isinstance(result, dict):
        return CO(**result)
    else:
        raise PreApplyError(f"Unexpected analysis result type: {type(result)}")


def handle_empty_plan() -> dict:
    """Handle empty plan (no changes) case."""
    from ...contracts.core_output import CoreOutput, RiskLevel
    from ...contracts.risk_attributes import RiskAttributes, BlastRadiusMetrics

    output = CoreOutput(
        version="1.0.0",
        risk_level=RiskLevel.LOW,
        risk_level_detailed="LOW",
        blast_radius_score=0.0,
        risk_action="AUTO_APPROVE",
        approval_required="NONE",
        affected_components=[],
        affected_count=0,
        risk_attributes=RiskAttributes(
            blast_radius=BlastRadiusMetrics(
                affected_resources=0,
                affected_components=0,
                changed_resources=0
            )
        ),
        risk_factors=[],
        recommendations=[]
    )
    return output.model_dump()


__all__ = ["resolve_file_path", "run_analysis", "format_error", "validate_resource_id", "validate_plan_json"]
