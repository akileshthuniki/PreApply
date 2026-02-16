"""Pydantic model for final output JSON (versioned, stable, explicit)."""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
from .risk_attributes import RiskAttributes


class RiskLevel(str, Enum):
    """Risk level enumeration for policy matching (4-tier)."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


def get_legacy_risk_level(detailed: str) -> RiskLevel:
    """Map 6-tier detailed level to 4-tier legacy enum for policy compatibility."""
    if detailed in ("CRITICAL-CATASTROPHIC", "CRITICAL"):
        return RiskLevel.CRITICAL
    elif detailed in ("HIGH-SEVERE", "HIGH"):
        return RiskLevel.HIGH
    elif detailed == "MEDIUM":
        return RiskLevel.MEDIUM
    else:
        return RiskLevel.LOW


class CoreOutput(BaseModel):
    """Core output contract - versioned, stable, explicit."""
    version: str = Field(default="1.0.0", description="Output contract version")
    risk_level: RiskLevel = Field(..., description="Overall risk level (4-tier for policy matching)")
    risk_level_detailed: Optional[str] = Field(default=None, description="6-tier level: CRITICAL-CATASTROPHIC, CRITICAL, HIGH-SEVERE, HIGH, MEDIUM, LOW")
    blast_radius_score: float = Field(..., ge=0, description="Blast radius score (0-250+, no cap)")
    risk_action: Optional[str] = Field(default=None, description="Recommended action: HARD_BLOCK, SOFT_BLOCK, REQUIRE_APPROVAL, REQUIRE_PEER_REVIEW, AUTO_APPROVE")
    approval_required: Optional[str] = Field(default=None, description="Human-readable approval requirement")
    affected_count: int = Field(default=0, ge=0, description="Number of resources affected (downstream of changes)")
    deletion_count: int = Field(default=0, ge=0, description="Number of resources being deleted")
    affected_components: List[str] = Field(default_factory=list, description="List of affected component identifiers")
    risk_attributes: RiskAttributes = Field(..., description="Structured risk attributes")
    risk_factors: List[str] = Field(default_factory=list, description="[DEPRECATED] Use risk_attributes")
    recommendations: List[str] = Field(default_factory=list, description="Deterministic recommendations")
    
    class Config:
        """Pydantic config."""
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "version": "1.0.0",
                "risk_level": "HIGH",
                "risk_level_detailed": "HIGH-SEVERE",
                "blast_radius_score": 82.0,
                "risk_action": "REQUIRE_APPROVAL",
                "approval_required": "SENIOR_ENGINEER + ARCHITECT",
                "affected_components": ["shared-vpc", "payments-api", "auth-service"],
                "affected_count": 15,
                "risk_factors": [
                    "Shared ALB modification",
                    "Cross-module dependency",
                    "Delete action detected"
                ],
                "recommendations": [
                    "Isolate ALB per service",
                    "Review change impact before applying"
                ]
            }
        }

