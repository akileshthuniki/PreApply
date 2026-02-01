"""Build directed dependency graph from normalized resources."""

import networkx as nx
from typing import List, Dict, Set, Optional
from ..ingest.models import NormalizedResource
from ..utils.errors import GraphConstructionError
from ..utils.logging import get_logger

logger = get_logger("graph.dependency_graph")


class DependencyGraph:
    """Directed dependency graph: nodes=resources, edges=dependencies."""
    
    def __init__(self):
        self.graph = nx.DiGraph()
        self._resource_map: Dict[str, NormalizedResource] = {}
    
    def add_resource(self, resource: NormalizedResource) -> None:
        """Add a resource to the graph."""
        node_id = self.get_node_id(resource)
        self.graph.add_node(node_id, resource=resource)
        self._resource_map[node_id] = resource
        
        for dep_address in resource.depends_on:
            dep_node_id = self._find_dependency_node(dep_address, resource)
            if dep_node_id:
                self.graph.add_edge(node_id, dep_node_id)
                logger.debug(f"Added dependency edge: {node_id} -> {dep_node_id}")
    
    def get_node_id(self, resource: NormalizedResource) -> str:
        """Generate unique node ID for a resource."""
        if resource.module:
            return f"{resource.module}.{resource.id}"
        return resource.id
    
    def _find_dependency_node(self, dep_address: str, source_resource: NormalizedResource) -> Optional[str]:
        """Find node ID for dependency address (handles full/relative/type-only refs)."""
        if dep_address in self._resource_map:
            return self.get_node_id(self._resource_map[dep_address])
        
        if source_resource.module:
            module_prefixed = f"{source_resource.module}.{dep_address}"
            if module_prefixed in self._resource_map:
                return self.get_node_id(self._resource_map[module_prefixed])
        
        for node_id, resource in self._resource_map.items():
            if resource.id == dep_address or resource.type == dep_address:
                return node_id
        
        logger.debug(f"Dependency not found in graph: {dep_address}")
        return None
    
    def build_from_resources(self, resources: List[NormalizedResource]) -> None:
        """Build complete dependency graph from list of resources."""
        try:
            for resource in resources:
                self.add_resource(resource)
            
            for resource in resources:
                node_id = self.get_node_id(resource)
                for dep_address in resource.depends_on:
                    dep_node_id = self._find_dependency_node(dep_address, resource)
                    if dep_node_id and not self.graph.has_edge(node_id, dep_node_id):
                        self.graph.add_edge(node_id, dep_node_id)
            
            logger.info(f"Built dependency graph with {self.graph.number_of_nodes()} nodes and {self.graph.number_of_edges()} edges")
            
        except Exception as e:
            raise GraphConstructionError(f"Failed to build dependency graph: {e}")
    
    def get_downstream_resources(self, resource_id: str) -> Set[str]:
        """Get all resources that depend on the given resource (downstream)."""
        if resource_id not in self.graph:
            return set()
        
        downstream = set()
        direct_predecessors = list(self.graph.predecessors(resource_id))
        
        for node in direct_predecessors:
            downstream.add(node)
            downstream.update(nx.ancestors(self.graph, node))
        
        return downstream
    
    def get_upstream_resources(self, resource_id: str) -> Set[str]:
        """Get all resources that the given resource depends on (upstream)."""
        if resource_id not in self.graph:
            return set()
        
        upstream = set()
        for node in nx.ancestors(self.graph, resource_id):
            upstream.add(node)
        
        return upstream
    
    def get_resource(self, node_id: str) -> Optional[NormalizedResource]:
        """Get normalized resource by node ID."""
        return self._resource_map.get(node_id)
    
    def get_all_resources(self) -> List[NormalizedResource]:
        """Get all resources in the graph."""
        return list(self._resource_map.values())
    
    def get_changed_resources(self) -> List[NormalizedResource]:
        """Get all resources with non-NO_OP actions."""
        from ..ingest.models import ResourceAction
        return [
            resource for resource in self._resource_map.values()
            if resource.action != ResourceAction.NO_OP
        ]

