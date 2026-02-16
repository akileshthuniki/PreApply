"""Policy engine - deterministic policy evaluation."""

from typing import List, Optional
from ..contracts.core_output import CoreOutput, RiskLevel
from ..presentation.explanation_ids import ExplanationID
from ..utils.errors import PreApplyError
from ..utils.logging import get_logger
from .models import Policy, MatchRule, Action, PolicyResult, PolicyEvaluationResult
from .loader import load_policies

logger = get_logger("policy.engine")


def evaluate_policies(
    output: CoreOutput,
    explanation_id: ExplanationID,
    policies: List[Policy],
    resource_id: Optional[str] = None,
    resource_type: Optional[str] = None
) -> PolicyEvaluationResult:
    """
    Evaluate policies against analysis output.
    
    Args:
        output: CoreOutput from analysis
        explanation_id: Explanation ID for this analysis
        policies: List of policies to evaluate
        resource_id: Optional resource ID (for resource-specific checks)
        resource_type: Optional resource type (for resource-specific checks)
        
    Returns:
        PolicyEvaluationResult with evaluation results
    """
    results = []
    failure_count = 0
    warning_count = 0
    
    for policy in policies:
        matched = _match_policy(policy.match, output, explanation_id, resource_type)
        
        if matched:
            result = PolicyResult(
                policy_id=policy.id,
                matched=True,
                action=policy.action,
                explanation=f"Policy '{policy.id}': {policy.description}"
            )
            results.append(result)
            
            if policy.action == Action.FAIL:
                failure_count += 1
            elif policy.action == Action.WARN:
                warning_count += 1
        
        else:
            result = PolicyResult(
                policy_id=policy.id,
                matched=False,
                action=policy.action,
                explanation=f"Policy '{policy.id}' did not match"
            )
            results.append(result)
    
    passed = failure_count == 0
    
    return PolicyEvaluationResult(
        passed=passed,
        results=results,
        failure_count=failure_count,
        warning_count=warning_count
    )


def _match_policy(
    match_rule: MatchRule,
    output: CoreOutput,
    explanation_id: ExplanationID,
    resource_type: Optional[str] = None
) -> bool:
    """
    Check if a match rule matches the analysis output.
    
    Args:
        match_rule: Match rule to evaluate
        output: CoreOutput from analysis
        explanation_id: Explanation ID
        resource_type: Optional resource type
        
    Returns:
        True if rule matches
    """
    # Check explanation_id match
    if match_rule.explanation_id is not None:
        if explanation_id.value != match_rule.explanation_id:
            return False
    
    # Check risk_level match
    if match_rule.risk_level is not None:
        output_risk = output.risk_level
        if isinstance(output_risk, str):
            output_risk = RiskLevel(output_risk)
        if output_risk != match_rule.risk_level:
            return False
    
    # Check resource_type match
    if match_rule.resource_type is not None:
        if resource_type is None:
            # Try to extract from risk_attributes
            resource_type = _extract_resource_type(output)
        if resource_type != match_rule.resource_type:
            return False
    
    # Check action_type match
    if match_rule.action_type is not None:
        if not output.risk_attributes.action_types:
            return False
        if match_rule.action_type not in output.risk_attributes.action_types:
            return False

    # Check has_sensitive_deletions match
    if match_rule.has_sensitive_deletions is True:
        sensitive = getattr(output.risk_attributes, "sensitive_deletions", []) or []
        if not sensitive:
            return False

    # Check has_security_exposures match
    if match_rule.has_security_exposures is True:
        exposures = getattr(output.risk_attributes, "security_exposures", []) or []
        if not exposures:
            return False

    return True


def _extract_resource_type(output: CoreOutput) -> Optional[str]:
    """Extract resource type from output (for resource-specific policies)."""
    attrs = output.risk_attributes
    
    # Try shared dependencies first
    if attrs.shared_dependencies:
        return attrs.shared_dependencies[0].resource_type
    
    # Try critical infrastructure
    if attrs.critical_infrastructure:
        return attrs.critical_infrastructure[0].resource_type
    
    return None


def check_policies(
    output: CoreOutput,
    explanation_id: ExplanationID,
    policy_file: str,
    resource_id: Optional[str] = None
) -> PolicyEvaluationResult:
    """
    Check policies against analysis output (convenience function).
    
    Args:
        output: CoreOutput from analysis
        explanation_id: Explanation ID for this analysis
        policy_file: Path to policy YAML file
        resource_id: Optional resource ID (for resource-specific checks)
        
    Returns:
        PolicyEvaluationResult with evaluation results
    """
    policies = load_policies(policy_file)
    
    # Extract resource type if resource_id provided
    resource_type = None
    if resource_id:
        resource_type = _extract_resource_type_from_id(output, resource_id)
    
    return evaluate_policies(output, explanation_id, policies, resource_id, resource_type)


def _extract_resource_type_from_id(output: CoreOutput, resource_id: str) -> Optional[str]:
    """Extract resource type for a given resource ID."""
    attrs = output.risk_attributes
    
    # Check shared dependencies
    for dep in attrs.shared_dependencies:
        if dep.resource_id == resource_id or resource_id in dep.resource_id:
            return dep.resource_type
    
    # Check critical infrastructure
    for crit in attrs.critical_infrastructure:
        if crit.resource_id == resource_id or resource_id in crit.resource_id:
            return crit.resource_type
    
    return None

