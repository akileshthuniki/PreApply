"""Explanation ID catalog - formalized vocabulary for deterministic explanations."""

from enum import Enum
from typing import Optional


class ExplanationID(str, Enum):
    """
    Stable identifiers for explanation types.
    
    These IDs correspond to explanation types, not instances.
    A single ID applies to many plans, keeping the explanation surface finite.
    """
    
    # Overall explanations
    SHARED_INFRASTRUCTURE_CHANGE = "SHARED_INFRASTRUCTURE_CHANGE"
    CRITICAL_SHARED_DEPENDENCY_MODIFICATION = "CRITICAL_SHARED_DEPENDENCY_MODIFICATION"
    SHARED_DEPENDENCY_MODIFICATION = "SHARED_DEPENDENCY_MODIFICATION"
    CRITICAL_INFRASTRUCTURE_MODIFICATION = "CRITICAL_INFRASTRUCTURE_MODIFICATION"
    DELETE_OPERATION_DETECTED = "DELETE_OPERATION_DETECTED"
    SINGLE_RESOURCE_LOW_RISK = "SINGLE_RESOURCE_LOW_RISK"
    
    # Resource-level explanations
    RESOURCE_CRITICAL_SHARED_DEPENDENCY = "RESOURCE_CRITICAL_SHARED_DEPENDENCY"
    RESOURCE_SHARED_CRITICAL = "RESOURCE_SHARED_CRITICAL"
    RESOURCE_SHARED_NON_CRITICAL = "RESOURCE_SHARED_NON_CRITICAL"
    RESOURCE_CRITICAL_NO_DEPENDENTS = "RESOURCE_CRITICAL_NO_DEPENDENTS"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"


# Explanation ID metadata
EXPLANATION_DESCRIPTIONS = {
    ExplanationID.SHARED_INFRASTRUCTURE_CHANGE: "Multiple shared infrastructure components are being modified",
    ExplanationID.CRITICAL_SHARED_DEPENDENCY_MODIFICATION: "A critical shared dependency with multiple dependents is being modified",
    ExplanationID.SHARED_DEPENDENCY_MODIFICATION: "A shared dependency is being modified",
    ExplanationID.CRITICAL_INFRASTRUCTURE_MODIFICATION: "Critical infrastructure is being modified",
    ExplanationID.DELETE_OPERATION_DETECTED: "Delete operations detected in plan",
    ExplanationID.SINGLE_RESOURCE_LOW_RISK: "Single resource change with low risk",
    ExplanationID.RESOURCE_CRITICAL_SHARED_DEPENDENCY: "Resource is both critical and shared with many dependents",
    ExplanationID.RESOURCE_SHARED_CRITICAL: "Resource is shared and critical",
    ExplanationID.RESOURCE_SHARED_NON_CRITICAL: "Resource is shared but not critical",
    ExplanationID.RESOURCE_CRITICAL_NO_DEPENDENTS: "Resource is critical but has no dependents",
    ExplanationID.RESOURCE_NOT_FOUND: "Requested resource not found in analysis",
}


def get_explanation_description(explanation_id: ExplanationID) -> str:
    """Get one-line description for an explanation ID."""
    return EXPLANATION_DESCRIPTIONS.get(explanation_id, "Unknown explanation type")

