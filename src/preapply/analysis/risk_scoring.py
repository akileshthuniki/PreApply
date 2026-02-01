"""Quantify risk using config weights (deterministic)."""

from typing import Dict, Any, List, Set
from ..ingest.models import NormalizedResource, ResourceAction
from ..graph.dependency_graph import DependencyGraph
from .shared_resources import detect_shared_resources
from .blast_radius import calculate_blast_radius
from .risk_reasons import generate_risk_reason, generate_critical_risk_reason
from ..contracts.risk_attributes import RiskAttributes, BlastRadiusMetrics, SharedDependency, CriticalInfrastructure
from ..utils.logging import get_logger

logger = get_logger("analysis.risk_scoring")


def calculate_risk_score(
    graph: DependencyGraph,
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """Calculate risk score based on deterministic heuristics."""
    blast_radius_config = config.get("blast_radius", {})
    risk_levels_config = config.get("risk_levels", {})
    
    changed_resources = graph.get_changed_resources()
    
    if not changed_resources:
        return {
            "blast_radius_score": 0,
            "risk_level": "LOW",
            "contributing_factors": []
        }
    
    blast_radius = calculate_blast_radius(graph, changed_resources)
    shared_resources = detect_shared_resources(graph, config)
    
    changed_shared = []
    for resource in changed_resources:
        if resource in shared_resources:
            changed_shared.append(resource)
    
    score = 0
    factors = []
    score_breakdown = {}
    
    critical_types = config.get("shared_resources", {}).get("critical_types", [])
    critical_multiplier = blast_radius_config.get("critical_infrastructure_multiplier", 1.3)
    base_shared_weight = blast_radius_config.get("shared_resource_weight", 30)
    shared_dependencies: List[SharedDependency] = []
    if changed_shared:
        shared_penalty = 0
        for shared in changed_shared:
            node_id = graph.get_node_id(shared)
            dependents_count = len(graph.get_downstream_resources(node_id))
            is_critical = shared.type in critical_types
            
            # Base weight for shared resource
            resource_weight = base_shared_weight
            multiplier_applied = None
            
            # Apply critical multiplier if this is critical infrastructure
            if is_critical:
                resource_weight = int(resource_weight * critical_multiplier)
                multiplier_applied = critical_multiplier
            
            shared_penalty += resource_weight
            
            # Build structured signal with deterministic risk reason
            resource_id = shared.id if not shared.module else f"{shared.module}.{shared.id}"
            risk_reason = generate_risk_reason(
                resource_type=shared.type,
                dependents=dependents_count,
                is_shared=True,
                is_critical=is_critical
            )
            shared_dependencies.append(SharedDependency(
                resource_id=resource_id,
                resource_type=shared.type,
                dependents=dependents_count,
                is_critical=is_critical,
                multiplier_applied=multiplier_applied,
                risk_reason=risk_reason
            ))
            
            # Keep backward compatibility string
            factors.append(f"Shared resource modified: {resource_id} ({dependents_count} dependents)")
        
        score += shared_penalty
        score_breakdown["shared_penalty"] = shared_penalty
    
    # Build critical infrastructure list (non-shared critical resources) with risk reasons
    critical_infrastructure: List[CriticalInfrastructure] = []
    changed_critical = [r for r in changed_resources if r.type in critical_types and r not in changed_shared]
    if changed_critical:
        # Apply smaller base weight with critical multiplier for non-shared critical resources
        critical_base_weight = int(base_shared_weight * 0.5)  # Half of base shared weight
        critical_penalty = 0
        for critical in changed_critical:
            resource_weight = int(critical_base_weight * critical_multiplier)
            critical_penalty += resource_weight
            resource_id = critical.id if not critical.module else f"{critical.module}.{critical.id}"
            risk_reason = generate_critical_risk_reason(critical.type)
            critical_infrastructure.append(CriticalInfrastructure(
                resource_id=resource_id,
                resource_type=critical.type,
                risk_reason=risk_reason
            ))
            # Keep backward compatibility string
            factors.append(f"Critical infrastructure modified: {resource_id}")
        
        score += critical_penalty
        score_breakdown["critical_type_penalty"] = critical_penalty
    
    # Build action types list (structured)
    action_types: List[str] = []
    action_multiplier: float = None
    
    delete_multiplier = blast_radius_config.get("delete_action_multiplier", 2.0)
    update_multiplier = blast_radius_config.get("update_action_multiplier", 1.5)
    create_multiplier = blast_radius_config.get("create_action_multiplier", 1.0)
    
    has_delete = any(r.action == ResourceAction.DELETE for r in changed_resources)
    has_update = any(r.action == ResourceAction.UPDATE for r in changed_resources)
    has_create = any(r.action == ResourceAction.CREATE for r in changed_resources)
    
    if has_delete:
        action_types.append("DELETE")
        action_multiplier = delete_multiplier
    if has_update:
        action_types.append("UPDATE")
        if action_multiplier is None:
            action_multiplier = update_multiplier
    if has_create:
        action_types.append("CREATE")
        if action_multiplier is None:
            action_multiplier = create_multiplier
    
    # Base score from affected count
    affected_count = blast_radius["affected_count"]
    downstream_weight = blast_radius_config.get("downstream_service_weight", 10)
    base_score = min(affected_count * downstream_weight, 50)  # Cap at 50
    score += base_score
    score_breakdown["base_score"] = base_score
    
    if affected_count > 0:
        factors.append(f"{affected_count} resources affected")
    
    # Apply action multiplier
    score_before_multiplier = score
    if action_multiplier:
        score = int(score * action_multiplier)
        score_breakdown["multiplier"] = action_multiplier
        if has_delete:
            factors.append("Delete action detected")
        elif has_update:
            factors.append("Update action detected")
    
    score_breakdown["score_before_multiplier"] = score_before_multiplier
    score_breakdown["score_after_multiplier"] = score
    
    # Cap score at 100
    score = min(score, 100)
    score_breakdown["final_score"] = score
    
    # Determine risk level
    low_threshold = risk_levels_config.get("low", 30)
    medium_threshold = risk_levels_config.get("medium", 60)
    
    if score <= low_threshold:
        risk_level = "LOW"
    elif score <= medium_threshold:
        risk_level = "MEDIUM"
    else:
        risk_level = "HIGH"
    
    # Build structured risk attributes
    risk_attributes = RiskAttributes(
        blast_radius=BlastRadiusMetrics(
            affected_resources=affected_count,
            affected_components=len(blast_radius["affected_components"]),
            changed_resources=len(changed_resources)
        ),
        shared_dependencies=shared_dependencies,
        critical_infrastructure=critical_infrastructure,
        action_types=action_types,
        action_multiplier=action_multiplier
    )
    
    result = {
        "blast_radius_score": score,
        "risk_level": risk_level,
        "contributing_factors": factors,  # Backward compatibility
        "affected_count": affected_count,
        "affected_components": blast_radius["affected_components"],
        "risk_attributes": risk_attributes  # New structured signals
    }
    
    logger.info(f"Risk score calculated: {score} ({risk_level})")
    return result

