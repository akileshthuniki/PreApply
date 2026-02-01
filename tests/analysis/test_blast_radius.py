"""Tests for blast radius calculation."""

import pytest
from preapply.analysis.blast_radius import calculate_blast_radius
from preapply.graph.dependency_graph import DependencyGraph
from preapply.ingest.models import NormalizedResource, ResourceAction


@pytest.fixture
def sample_graph():
    """Create sample dependency graph."""
    resources = [
        NormalizedResource(
            id="aws_lb.shared",
            type="aws_lb",
            action=ResourceAction.UPDATE,
            depends_on=[],
            module=None
        ),
        NormalizedResource(
            id="aws_lb_target_group.api",
            type="aws_lb_target_group",
            action=ResourceAction.UPDATE,
            depends_on=["aws_lb.shared"],
            module="payments"
        ),
        NormalizedResource(
            id="aws_lb_target_group.service",
            type="aws_lb_target_group",
            action=ResourceAction.UPDATE,
            depends_on=["aws_lb.shared"],
            module="auth"
        )
    ]
    
    graph = DependencyGraph()
    graph.build_from_resources(resources)
    return graph


class TestBlastRadius:
    """Test blast radius calculation."""
    
    def test_calculate_blast_radius(self, sample_graph):
        """Test calculating blast radius for changed resources."""
        changed = [
            sample_graph.get_resource("aws_lb.shared")
        ]
        changed = [r for r in changed if r is not None]
        
        result = calculate_blast_radius(sample_graph, changed)
        
        assert "affected_count" in result
        assert "affected_components" in result
        assert "changed_count" in result
        assert result["changed_count"] == 1
        assert result["affected_count"] >= 1
    
    def test_calculate_blast_radius_empty(self, sample_graph):
        """Test calculating blast radius with no changes."""
        result = calculate_blast_radius(sample_graph, [])
        
        assert result["affected_count"] == 0
        assert result["affected_components"] == []
        assert result["changed_count"] == 0
    
    def test_calculate_blast_radius_multiple_changes(self, sample_graph):
        """Test calculating blast radius with multiple changed resources."""
        changed = [
            sample_graph.get_resource("aws_lb.shared"),
            sample_graph.get_resource("payments.aws_lb_target_group.api")
        ]
        changed = [r for r in changed if r is not None]
        
        result = calculate_blast_radius(sample_graph, changed)
        
        assert result["changed_count"] == len(changed)
        assert result["affected_count"] >= len(changed)
