"""Generate deterministic risk reasons during analysis (not presentation)."""

from typing import Optional
from ..ingest.models import NormalizedResource


def generate_risk_reason(
    resource_type: str,
    dependents: int,
    is_shared: bool,
    is_critical: bool
) -> str:
    """Generate deterministic risk reason based on resource characteristics."""
    resource_type_lower = resource_type.lower()
    
    if "vpc" in resource_type_lower:
        if dependents >= 5:
            return "Broad blast radius across networking layer"
        return "Core networking infrastructure"
    
    if "nat" in resource_type_lower or ("gateway" in resource_type_lower and "internet" in resource_type_lower):
        return "Internet egress for private workloads"
    
    if "nat_gateway" in resource_type_lower:
        return "Internet egress for private workloads"
    
    if "subnet" in resource_type_lower:
        return "Network segmentation boundary"
    
    if any(x in resource_type_lower for x in ["lb", "alb", "nlb", "elb"]):
        if is_shared:
            return "Impacts multiple load-balanced services"
        return "Traffic routing point"
    
    if "security_group" in resource_type_lower or "firewall" in resource_type_lower:
        if is_shared:
            return "Shared security boundary"
        return "Access control enforcement"

    if "db_instance" in resource_type_lower or "database" in resource_type_lower:
        return "Data persistence - deletion causes data loss"
    if "s3_bucket" in resource_type_lower:
        return "Object storage - deletion causes data loss"
    
    if is_shared and dependents >= 3:
        return f"Shared resource with {dependents} dependents"
    
    if is_critical:
        return "Critical infrastructure component"
    
    if is_shared:
        return f"Shared resource affecting {dependents} dependents"
    
    return "Infrastructure component change"


def generate_critical_risk_reason(resource_type: str) -> str:
    """Generate risk reason for critical infrastructure (non-shared)."""
    resource_type_lower = resource_type.lower()
    
    if "vpc" in resource_type_lower:
        return "Core networking infrastructure"
    
    if "nat" in resource_type_lower or "gateway" in resource_type_lower:
        return "Internet egress for private workloads"
    
    if any(x in resource_type_lower for x in ["lb", "alb", "nlb", "elb"]):
        return "Traffic routing point"
    
    if "security_group" in resource_type_lower or "firewall" in resource_type_lower:
        return "Access control enforcement"

    if "db_instance" in resource_type_lower or "database" in resource_type_lower:
        return "Data persistence - deletion causes data loss"
    if "s3_bucket" in resource_type_lower:
        return "Object storage - deletion causes data loss"

    return "Critical infrastructure component"

