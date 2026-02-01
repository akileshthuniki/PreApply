"""Traverse graph to calculate affected component count."""

from typing import List, Set, Dict, Any
from ..ingest.models import NormalizedResource
from ..graph.dependency_graph import DependencyGraph
from ..utils.logging import get_logger

logger = get_logger("analysis.blast_radius")


def calculate_blast_radius(
    graph: DependencyGraph,
    changed_resources: List[NormalizedResource]
) -> Dict[str, Any]:
    """Calculate blast radius: downstream of changed resources only."""
    if not changed_resources:
        return {
            "affected_count": 0,
            "affected_components": [],
            "changed_count": 0
        }
    
    changed_node_ids = {graph.get_node_id(r) for r in changed_resources}
    affected_node_ids = set()
    
    for changed_node_id in changed_node_ids:
        downstream = graph.get_downstream_resources(changed_node_id)
        affected_node_ids.update(downstream)
        affected_node_ids.add(changed_node_id)
    
    affected_components = []
    component_to_resources = {}
    for node_id in affected_node_ids:
        resource = graph.get_resource(node_id)
        if resource:
            component = resource.module if resource.module else resource.type
            if component not in affected_components:
                affected_components.append(component)
                component_to_resources[component] = []
            component_to_resources[component].append(resource.id)
    
    result = {
        "affected_count": len(affected_node_ids),
        "affected_components": affected_components,
        "changed_count": len(changed_resources)
    }
    
    logger.info(f"Blast radius: {result['affected_count']} resources affected across {len(affected_components)} components (from {result['changed_count']} changed resources)")
    return result
