"""Policy models - declarative policy definitions."""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from ..contracts.core_output import RiskLevel
from ..presentation.explanation_ids import ExplanationID


class Action(str, Enum):
    """Policy action to take when policy matches."""
    ALLOW = "allow"
    FAIL = "fail"
    WARN = "warn"


class MatchRule(BaseModel):
    """Rule for matching policies against analysis output."""
    
    explanation_id: Optional[str] = Field(None, description="Match explanation ID (exact match)")
    risk_level: Optional[RiskLevel] = Field(None, description="Match risk level")
    resource_type: Optional[str] = Field(None, description="Match resource type (e.g., 'aws_vpc')")
    action_type: Optional[str] = Field(None, description="Match action type (CREATE, UPDATE, DELETE)")
    has_sensitive_deletions: Optional[bool] = Field(None, description="Match when sensitive_deletions is non-empty")
    has_security_exposures: Optional[bool] = Field(None, description="Match when security_exposures is non-empty")
    
    class Config:
        use_enum_values = True


class Policy(BaseModel):
    """Policy definition - declarative, no code."""
    
    id: str = Field(..., description="Unique policy identifier")
    description: str = Field(..., description="Human-readable policy description")
    match: MatchRule = Field(..., description="Matching rules")
    action: Action = Field(..., description="Action to take when policy matches")
    
    class Config:
        use_enum_values = True


class PolicyResult(BaseModel):
    """Result of policy evaluation."""
    
    policy_id: str = Field(..., description="ID of the policy that matched")
    matched: bool = Field(..., description="Whether the policy matched")
    action: Action = Field(..., description="Action to take")
    explanation: str = Field(..., description="Human-readable explanation of the match")


class PolicyEvaluationResult(BaseModel):
    """Complete result of policy evaluation."""
    
    passed: bool = Field(..., description="Whether all policies passed")
    results: List[PolicyResult] = Field(default_factory=list, description="Individual policy results")
    failure_count: int = Field(default=0, description="Number of policies that failed")
    warning_count: int = Field(default=0, description="Number of policies that warned")
    
    class Config:
        use_enum_values = True

