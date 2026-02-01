"""Tests for policy engine."""

import pytest
from preapply.policy.engine import evaluate_policies, _match_policy
from preapply.policy.models import Policy, MatchRule, Action
from preapply.contracts.core_output import CoreOutput, RiskLevel
from preapply.contracts.risk_attributes import RiskAttributes, BlastRadiusMetrics
from preapply.presentation.explanation_ids import ExplanationID


@pytest.fixture
def sample_core_output():
    """Create sample CoreOutput."""
    return CoreOutput(
        version="1.0.0",
        risk_level=RiskLevel.HIGH,
        blast_radius_score=82,
        affected_count=11,
        affected_components=["shared-vpc"],
        risk_attributes=RiskAttributes(
            blast_radius=BlastRadiusMetrics(
                affected_resources=11,
                affected_components=9,
                changed_resources=4
            ),
            shared_dependencies=[],
            critical_infrastructure=[],
            action_types=["UPDATE", "DELETE"]
        ),
        recommendations=["Test recommendation"]
    )


class TestPolicyEngine:
    """Test policy evaluation."""
    
    def test_evaluate_policies_no_match(self, sample_core_output):
        """Test policy evaluation with no matching policies."""
        policies = [
            Policy(
                id="test-policy",
                description="Test policy",
                match=MatchRule(risk_level="LOW"),
                action=Action.FAIL
            )
        ]
        
        result = evaluate_policies(
            sample_core_output,
            ExplanationID.SHARED_INFRASTRUCTURE_CHANGE,
            policies
        )
        
        assert result.passed is True
        assert result.failure_count == 0
        assert len(result.results) == 1
        assert result.results[0].matched is False
    
    def test_evaluate_policies_match_fail(self, sample_core_output):
        """Test policy evaluation with matching FAIL policy."""
        policies = [
            Policy(
                id="high-risk-policy",
                description="Block high risk changes",
                match=MatchRule(risk_level="HIGH"),
                action=Action.FAIL
            )
        ]
        
        result = evaluate_policies(
            sample_core_output,
            ExplanationID.SHARED_INFRASTRUCTURE_CHANGE,
            policies
        )
        
        assert result.passed is False
        assert result.failure_count == 1
        assert result.results[0].matched is True
        assert result.results[0].action == Action.FAIL
    
    def test_evaluate_policies_match_warn(self, sample_core_output):
        """Test policy evaluation with matching WARN policy."""
        policies = [
            Policy(
                id="warn-policy",
                description="Warn on high risk",
                match=MatchRule(risk_level="HIGH"),
                action=Action.WARN
            )
        ]
        
        result = evaluate_policies(
            sample_core_output,
            ExplanationID.SHARED_INFRASTRUCTURE_CHANGE,
            policies
        )
        
        assert result.passed is True  # WARN doesn't fail
        assert result.warning_count == 1
        assert result.results[0].matched is True
