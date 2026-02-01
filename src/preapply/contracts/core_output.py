"""Pydantic model for final output JSON (versioned, stable, explicit)."""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
from .risk_attributes import RiskAttributes


class RiskLevel(str, Enum):
    """Risk level enumeration."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class CoreOutput(BaseModel):
    """Core output contract - versioned, stable, explicit."""
    version: str = Field(default="1.0.0", description="Output contract version")
    risk_level: RiskLevel = Field(..., description="Overall risk level")
    blast_radius_score: int = Field(..., ge=0, le=100, description="Blast radius score (0-100)")
    affected_count: int = Field(default=0, ge=0, description="Number of resources affected (downstream of changes)")
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
                "blast_radius_score": 82,
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

