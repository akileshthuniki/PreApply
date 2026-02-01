"""Tests for prompt contract construction (deterministic)."""

import json
from pathlib import Path
import pytest
from preapply.contracts.core_output import CoreOutput
from preapply.ai.prompt import build_prompt, PromptContract


@pytest.fixture
def sample_core_output():
    """Load sample CoreOutput from fixture."""
    fixture_path = Path(__file__).parent.parent / "report" / "fixtures" / "core_output.sample.json"
    with open(fixture_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return CoreOutput(**data)


class TestDeterministicPromptConstruction:
    """Test that prompt construction is deterministic."""
    
    def test_prompt_determinism(self, sample_core_output):
        """Same CoreOutput + same question → same prompt."""
        question = "What is the worst case impact?"
        
        prompt1 = build_prompt(sample_core_output, question)
        prompt2 = build_prompt(sample_core_output, question)
        
        assert prompt1 == prompt2, "Prompt construction must be deterministic"
    
    def test_prompt_contains_constraints(self, sample_core_output):
        """Prompt must contain explicit constraints."""
        prompt = build_prompt(sample_core_output, "Test question")
        
        # Must contain critical constraints
        assert "NOT allowed to change risk levels" in prompt
        assert "ADVISORY information only" in prompt
        assert "cannot override or modify" in prompt
    
    def test_prompt_contains_risk_level(self, sample_core_output):
        """Prompt must contain risk level."""
        prompt = build_prompt(sample_core_output, "Test question")
        
        assert "Risk Level:" in prompt
        assert str(sample_core_output.risk_level) in prompt
    
    def test_prompt_contains_explanation_id(self, sample_core_output):
        """Prompt must contain explanation ID."""
        prompt = build_prompt(sample_core_output, "Test question")
        
        assert "Explanation ID:" in prompt
    
    def test_prompt_contains_explanation_text(self, sample_core_output):
        """Prompt must contain deterministic explanation."""
        prompt = build_prompt(sample_core_output, "Test question")
        
        assert "Deterministic Explanation:" in prompt
    
    def test_prompt_contains_recommendations(self, sample_core_output):
        """Prompt must contain recommendations."""
        prompt = build_prompt(sample_core_output, "Test question")
        
        assert "Recommendations:" in prompt
        # Should contain at least one recommendation from sample
        if sample_core_output.recommendations:
            assert any(rec in prompt for rec in sample_core_output.recommendations)
    
    def test_prompt_contains_blast_radius(self, sample_core_output):
        """Prompt must contain blast radius summary."""
        prompt = build_prompt(sample_core_output, "Test question")
        
        assert "Blast Radius Summary:" in prompt
        assert str(sample_core_output.affected_count) in prompt
    
    def test_prompt_contains_user_question(self, sample_core_output):
        """Prompt must contain user's question."""
        question = "What is the impact of this change?"
        prompt = build_prompt(sample_core_output, question)
        
        assert "USER QUESTION:" in prompt
        assert question in prompt
