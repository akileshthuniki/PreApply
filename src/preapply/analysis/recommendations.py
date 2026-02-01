"""Generate deterministic advice based on patterns."""

from typing import List, Dict, Any
from ..ingest.models import NormalizedResource, ResourceAction
from ..graph.dependency_graph import DependencyGraph
from .shared_resources import detect_shared_resources, get_shared_resource_usage
from .blast_radius import calculate_blast_radius
from ..utils.logging import get_logger

logger = get_logger("analysis.recommendations")


def generate_recommendations(
    graph: DependencyGraph,
    risk_score: Dict[str, Any],
    config: Dict[str, Any]
) -> List[str]:
    """Generate deterministic recommendations based on detected patterns."""
    recommendations = []
    changed_resources = graph.get_changed_resources()
    
    shared_resources = detect_shared_resources(graph, config)
    changed_shared = [r for r in changed_resources if r in shared_resources]
    
    if changed_shared:
        for shared in changed_shared:
            usage = get_shared_resource_usage(graph, shared)
            if len(usage) > 1:
                rec = f"Isolate {shared.type} resource - currently shared across {len(usage)} modules"
                recommendations.append(rec)
    
    critical_types = config.get("shared_resources", {}).get("critical_types", [])
    deletes_on_critical = [
        r for r in changed_resources
        if r.action == ResourceAction.DELETE and r.type in critical_types
    ]
    
    if deletes_on_critical:
        for resource in deletes_on_critical:
            rec = f"High risk: Delete action on critical resource {resource.type}"
            recommendations.append(rec)
    
    blast_radius = calculate_blast_radius(graph, changed_resources)
    if blast_radius["affected_count"] > 10:
        rec = f"Large blast radius: {blast_radius['affected_count']} resources affected. Consider breaking into smaller changes."
        recommendations.append(rec)
    
    modules_affected = set()
    for resource in changed_resources:
        if resource.module:
            modules_affected.add(resource.module)
        else:
            modules_affected.add("root")
    
    if len(modules_affected) > 1:
        rec = f"Cross-module change detected affecting {len(modules_affected)} modules. Review module boundaries."
        recommendations.append(rec)
    
    if not recommendations and risk_score["risk_level"] != "LOW":
        recommendations.append("Review change impact before applying")
    
    logger.info(f"Generated {len(recommendations)} recommendations")
    return recommendations

