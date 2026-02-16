"""Structured risk attributes - facts separated from explanations."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class BlastRadiusMetrics(BaseModel):
    """Blast radius quantitative metrics."""
    affected_resources: int = Field(..., description="Number of resources affected (downstream of changes)")
    affected_components: int = Field(..., description="Number of unique component types affected")
    changed_resources: int = Field(..., description="Number of directly changed resources")


class SharedDependency(BaseModel):
    """A shared resource dependency signal."""
    resource_id: str = Field(..., description="Full resource identifier (e.g., 'aws_vpc.main' or 'module.vpc.aws_vpc.main')")
    resource_type: str = Field(..., description="Resource type (e.g., 'aws_vpc')")
    dependents: int = Field(..., description="Number of resources that depend on this shared resource")
    is_critical: bool = Field(default=False, description="Whether this resource type is considered critical infrastructure")
    multiplier_applied: Optional[float] = Field(default=None, description="Critical infrastructure multiplier applied (if critical)")
    risk_reason: str = Field(..., description="Deterministic risk reason generated during analysis (not presentation)")


class CriticalInfrastructure(BaseModel):
    """Critical infrastructure resource (non-shared)."""
    resource_id: str = Field(..., description="Full resource identifier")
    resource_type: str = Field(..., description="Resource type")
    risk_reason: str = Field(..., description="Deterministic risk reason generated during analysis")


class SensitiveDeletion(BaseModel):
    """A sensitive resource being deleted (critical stop)."""
    resource_id: str = Field(..., description="Full resource identifier")
    resource_type: str = Field(..., description="Resource type (e.g., aws_db_instance, aws_s3_bucket)")


class SecurityExposure(BaseModel):
    """Security exposure detected in plan (public exposure)."""
    resource_id: str = Field(..., description="Full resource identifier")
    resource_type: str = Field(..., description="Resource type")
    exposure_type: str = Field(..., description="Type of exposure (e.g., public_cidr, s3_public)")
    details: str = Field(..., description="Human-readable description")
    port_sensitive: bool = Field(default=False, description="True when Port 22 or 3389 exposed globally")
    port: Optional[int] = Field(default=None, description="Exposed port for penalty calculation (single port or sensitive from_port in range)")


class CostAlert(BaseModel):
    """Cost spike or scaling alert."""
    resource_id: str = Field(..., description="Full resource identifier")
    resource_type: str = Field(..., description="Resource type")
    reason: str = Field(..., description="Reason for alert (e.g., high_cost_creation, instance_scaling)")
    alert_type: str = Field(
        default="HIGH_COST_CREATION",
        description="Alert category: HIGH_COST_CREATION or INSTANCE_SCALING",
    )


class RiskBreakdown(BaseModel):
    """Production scorer breakdown - dimension scores and contributions."""
    primary_dimension: str = Field(..., description="Dimension with highest score (data, security, infrastructure, cost)")
    primary_score: float = Field(..., description="Score of primary dimension")
    interaction_multiplier: float = Field(..., description="1.0 + sum of interaction bonuses")
    blast_radius_contribution: float = Field(..., description="B × ω contribution to final score")
    dimensions: Dict[str, float] = Field(default_factory=dict, description="Per-dimension scores")


class RiskAttributes(BaseModel):
    """Structured risk attributes - facts separated from explanations."""
    blast_radius: BlastRadiusMetrics = Field(..., description="Blast radius quantitative metrics")
    shared_dependencies: List[SharedDependency] = Field(default_factory=list, description="List of shared resources that are being modified")
    critical_infrastructure: List[CriticalInfrastructure] = Field(default_factory=list, description="List of critical infrastructure resources being modified (non-shared)")
    sensitive_deletions: List[SensitiveDeletion] = Field(default_factory=list, description="Sensitive resources being deleted (critical stop)")
    security_exposures: List[SecurityExposure] = Field(default_factory=list, description="Security exposures (public CIDR, S3 public, etc.)")
    cost_alerts: List[CostAlert] = Field(default_factory=list, description="Cost spike or scaling alerts")
    action_types: List[str] = Field(default_factory=list, description="List of action types present (CREATE, UPDATE, DELETE)")
    action_multiplier: Optional[float] = Field(default=None, description="Action multiplier applied to base score")
    risk_breakdown: Optional[RiskBreakdown] = Field(default=None, description="Production scorer breakdown (dimensions, multiplier, blast)")

