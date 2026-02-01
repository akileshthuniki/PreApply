"""Deterministic explanation generator - converts structured data to human-readable explanations."""

from typing import List, Tuple
from ..contracts.core_output import CoreOutput, RiskLevel
from ..contracts.risk_attributes import SharedDependency, CriticalInfrastructure
from .explanation_ids import ExplanationID


def explain_overall(output: CoreOutput) -> str:
    """
    Generate overall risk explanation (deterministic, template-based).
    
    Args:
        output: CoreOutput from analysis
        
    Returns:
        Human-readable explanation string
    """
    explanation, _ = explain_overall_with_id(output)
    return explanation


def explain_overall_with_id(output: CoreOutput) -> Tuple[str, ExplanationID]:
    """
    Generate overall risk explanation with explanation ID.
    
    Args:
        output: CoreOutput from analysis
        
    Returns:
        Tuple of (explanation_text, explanation_id)
    """
    risk_level = output.risk_level
    if isinstance(risk_level, str):
        risk_level = RiskLevel(risk_level)
    
    attrs = output.risk_attributes
    
    # Build primary factors
    primary_factors = []
    
    if attrs.shared_dependencies:
        shared_count = len(attrs.shared_dependencies)
        if shared_count == 1:
            dep = attrs.shared_dependencies[0]
            primary_factors.append(f"modification of shared {dep.resource_type} ({dep.dependents} dependents)")
        else:
            primary_factors.append(f"{shared_count} shared dependencies")
    
    if attrs.critical_infrastructure:
        crit_count = len(attrs.critical_infrastructure)
        if crit_count == 1:
            crit = attrs.critical_infrastructure[0]
            primary_factors.append(f"modification of critical {crit.resource_type}")
        else:
            primary_factors.append(f"{crit_count} critical infrastructure components")
    
    if attrs.action_types:
        if "DELETE" in attrs.action_types:
            primary_factors.append("delete operations detected")
        elif "CREATE" in attrs.action_types:
            primary_factors.append("new resource creation")
    
    if not primary_factors:
        primary_factors.append("infrastructure changes")
    
    # Build blast radius context
    blast_radius = attrs.blast_radius
    blast_context = f"affecting {blast_radius.affected_resources} downstream resources"
    if blast_radius.affected_components > 1:
        blast_context += f" across {blast_radius.affected_components} component types"
    
    # Build explanation
    explanation = f"This change has {risk_level.value} risk"
    
    if primary_factors:
        factors_text = ", ".join(primary_factors)
        explanation += f" due to {factors_text}"
    
    explanation += f". The blast radius {blast_context}."
    
    # Add recommendations if available
    if output.recommendations:
        explanation += f" {output.recommendations[0]}"
    
    # Determine explanation ID
    explanation_id = _get_overall_explanation_id(attrs)
    
    return explanation, explanation_id


def _get_overall_explanation_id(attrs) -> ExplanationID:
    """Determine explanation ID for overall explanation."""
    if attrs.shared_dependencies and len(attrs.shared_dependencies) > 1:
        return ExplanationID.SHARED_INFRASTRUCTURE_CHANGE
    elif attrs.shared_dependencies:
        if attrs.shared_dependencies[0].is_critical:
            return ExplanationID.CRITICAL_SHARED_DEPENDENCY_MODIFICATION
        else:
            return ExplanationID.SHARED_DEPENDENCY_MODIFICATION
    elif attrs.critical_infrastructure:
        return ExplanationID.CRITICAL_INFRASTRUCTURE_MODIFICATION
    elif attrs.action_types and "DELETE" in attrs.action_types:
        return ExplanationID.DELETE_OPERATION_DETECTED
    else:
        return ExplanationID.SINGLE_RESOURCE_LOW_RISK


def explain_resource(output: CoreOutput, resource_id: str) -> str:
    """
    Generate resource-specific explanation (deterministic, template-based).
    
    Args:
        output: CoreOutput from analysis
        resource_id: Resource identifier to explain
        
    Returns:
        Human-readable explanation string
    """
    explanation, _ = explain_resource_with_id(output, resource_id)
    return explanation


def explain_resource_with_id(output: CoreOutput, resource_id: str) -> Tuple[str, ExplanationID]:
    """
    Generate resource-specific explanation with explanation ID.
    
    Args:
        output: CoreOutput from analysis
        resource_id: Resource identifier to explain
        
    Returns:
        Tuple of (explanation_text, explanation_id)
    """
    attrs = output.risk_attributes
    
    # Find resource in shared dependencies
    for dep in attrs.shared_dependencies:
        if dep.resource_id == resource_id or resource_id in dep.resource_id:
            explanation = _explain_shared_dependency(dep, attrs)
            explanation_id = _get_resource_explanation_id(dep, True)
            return explanation, explanation_id
    
    # Find resource in critical infrastructure
    for crit in attrs.critical_infrastructure:
        if crit.resource_id == resource_id or resource_id in crit.resource_id:
            explanation = _explain_critical_infrastructure(crit, attrs)
            explanation_id = ExplanationID.RESOURCE_CRITICAL_NO_DEPENDENTS
            return explanation, explanation_id
    
    # Resource not found
    return f"Resource '{resource_id}' not found in analysis results.", ExplanationID.RESOURCE_NOT_FOUND


def _get_resource_explanation_id(dep: SharedDependency, is_shared: bool) -> ExplanationID:
    """Determine explanation ID for resource explanation."""
    if is_shared and dep.is_critical:
        if dep.dependents > 5:
            return ExplanationID.RESOURCE_CRITICAL_SHARED_DEPENDENCY
        else:
            return ExplanationID.RESOURCE_SHARED_CRITICAL
    elif is_shared:
        return ExplanationID.RESOURCE_SHARED_NON_CRITICAL
    else:
        return ExplanationID.RESOURCE_CRITICAL_NO_DEPENDENTS


def _explain_shared_dependency(dep: SharedDependency, attrs) -> str:
    """Explain a shared dependency resource."""
    classification_parts = []
    if dep.is_critical:
        classification_parts.append("critical")
    classification_parts.append("shared")
    
    explanation = f"{dep.resource_id} is a {' and '.join(classification_parts)} resource"
    explanation += f" because {dep.risk_reason.lower()}"
    
    if dep.dependents > 0:
        explanation += f". It affects {dep.dependents} downstream resource"
        if dep.dependents > 1:
            explanation += "s"
    
    if attrs.action_types:
        explanation += f". Action type: {', '.join(attrs.action_types)}"
    
    return explanation


def _explain_critical_infrastructure(crit: CriticalInfrastructure, attrs) -> str:
    """Explain a critical infrastructure resource."""
    explanation = f"{crit.resource_id} is critical infrastructure"
    explanation += f" because {crit.risk_reason.lower()}"
    
    if attrs.action_types:
        explanation += f". Action type: {', '.join(attrs.action_types)}"
    
    return explanation


def generate_summary(output: CoreOutput) -> str:
    """
    Generate short paragraph summary (2-3 sentences, deterministic).
    
    Args:
        output: CoreOutput from analysis
        
    Returns:
        Short paragraph summary
    """
    summary, _ = generate_summary_with_id(output)
    return summary


def generate_summary_with_id(output: CoreOutput) -> Tuple[str, ExplanationID]:
    """
    Generate short paragraph summary with explanation ID.
    
    Args:
        output: CoreOutput from analysis
        
    Returns:
        Tuple of (summary_text, explanation_id)
    """
    risk_level = output.risk_level
    if isinstance(risk_level, str):
        risk_level = RiskLevel(risk_level)
    
    attrs = output.risk_attributes
    
    # Sentence 1: Risk level + primary driver
    primary_driver = _get_primary_driver(attrs)
    sentence1 = f"This change has {risk_level.value} risk due to {primary_driver}"
    
    # Sentence 2: Blast radius impact
    blast_radius = attrs.blast_radius
    sentence2 = f"The blast radius affects {blast_radius.affected_resources} resources"
    if blast_radius.affected_components > 1:
        sentence2 += f" across {blast_radius.affected_components} component types"
    sentence2 += "."
    
    # Sentence 3: Key recommendation (if any)
    sentences = [sentence1, sentence2]
    if output.recommendations:
        sentence3 = output.recommendations[0]
        sentences.append(sentence3)
    
    summary = ". ".join(sentences)
    explanation_id = _get_overall_explanation_id(attrs)  # Summary uses same ID as overall
    
    return summary, explanation_id


def _get_primary_driver(attrs) -> str:
    """Get primary risk driver description."""
    if attrs.shared_dependencies:
        dep = attrs.shared_dependencies[0]  # Highest priority shared dependency
        return f"modification of shared {dep.resource_type} infrastructure"
    
    if attrs.critical_infrastructure:
        crit = attrs.critical_infrastructure[0]
        return f"modification of critical {crit.resource_type} infrastructure"
    
    if attrs.action_types:
        if "DELETE" in attrs.action_types:
            return "delete operations"
        elif "CREATE" in attrs.action_types:
            return "new resource creation"
    
    return "infrastructure changes"


def list_resources(output: CoreOutput) -> List[str]:
    """
    List all resource IDs available for explanation.
    
    Args:
        output: CoreOutput from analysis
        
    Returns:
        List of resource IDs
    """
    resources = []
    attrs = output.risk_attributes
    
    for dep in attrs.shared_dependencies:
        resources.append(dep.resource_id)
    
    for crit in attrs.critical_infrastructure:
        resources.append(crit.resource_id)
    
    return sorted(resources)
