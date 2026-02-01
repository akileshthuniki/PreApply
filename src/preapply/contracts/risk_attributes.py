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


class RiskAttributes(BaseModel):
    """Structured risk attributes - facts separated from explanations."""
    blast_radius: BlastRadiusMetrics = Field(..., description="Blast radius quantitative metrics")
    shared_dependencies: List[SharedDependency] = Field(default_factory=list, description="List of shared resources that are being modified")
    critical_infrastructure: List[CriticalInfrastructure] = Field(default_factory=list, description="List of critical infrastructure resources being modified (non-shared)")
    action_types: List[str] = Field(default_factory=list, description="List of action types present (CREATE, UPDATE, DELETE)")
    action_multiplier: Optional[float] = Field(default=None, description="Action multiplier applied to base score")

