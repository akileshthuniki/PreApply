"""Detect coupling: resources used by multiple services/modules."""

from typing import List, Set, Dict, Any
from ..ingest.models import NormalizedResource
from ..graph.dependency_graph import DependencyGraph
from ..utils.logging import get_logger

logger = get_logger("analysis.shared_resources")


def detect_shared_resources(
    graph: DependencyGraph,
    config: Dict[str, Any]
) -> List[NormalizedResource]:
    """Detect shared resources: topology-based (2+ dependents)."""
    shared = []
    all_resources = graph.get_all_resources()
    
    for resource in all_resources:
        node_id = graph.get_node_id(resource)
        dependents = graph.get_downstream_resources(node_id)
        
        if len(dependents) >= 2:
            shared.append(resource)
            logger.debug(f"Resource {resource.id} is shared ({len(dependents)} dependents)")
    
    logger.info(f"Detected {len(shared)} shared resources (topology-based)")
    return shared


def get_shared_resource_usage(
    graph: DependencyGraph,
    shared_resource: NormalizedResource
) -> List[str]:
    """Get list of modules/services that use a shared resource."""
    node_id = graph.get_node_id(shared_resource)
    dependents = graph.get_downstream_resources(node_id)
    
    modules = set()
    for dep_node_id in dependents:
        dep_resource = graph.get_resource(dep_node_id)
        if dep_resource and dep_resource.module:
            modules.add(dep_resource.module)
        elif dep_resource:
            modules.add("root")
    
    return list(modules)

