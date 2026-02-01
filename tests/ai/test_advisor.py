"""Tests for AI advisor adapters (mocked)."""

import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest
from preapply.contracts.core_output import CoreOutput
from preapply.ai.base import AIAdvisor


@pytest.fixture
def sample_core_output():
    """Load sample CoreOutput from fixture."""
    fixture_path = Path(__file__).parent.parent / "report" / "fixtures" / "core_output.sample.json"
    with open(fixture_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return CoreOutput(**data)


class TestMockAIAdapter:
    """Test AI adapter interface with mocks."""
    
    def test_ai_advisor_interface(self, sample_core_output):
        """Test that AI advisor follows interface contract."""
        # Create mock advisor
        class MockAdvisor(AIAdvisor):
            def ask(self, core_output, question, max_tokens=None):
                return "Mock advisory response"
            
            def is_available(self):
                return True
        
        advisor = MockAdvisor()
        
        # Test interface
        assert advisor.is_available()
        response = advisor.ask(sample_core_output, "Test question")
        assert isinstance(response, str)
        assert "Mock advisory response" in response
    
    @patch('preapply.ai.openai.OPENAI_AVAILABLE', True)
    @patch('preapply.ai.openai.openai')
    def test_openai_adapter_mock(self, mock_openai_module, sample_core_output):
        """Test OpenAI adapter with mocked API."""
        # Mock OpenAI client
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "OpenAI advisory response"
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_module.OpenAI.return_value = mock_client
        
        # Import and test
        from preapply.ai.openai import OpenAIAdvisor
        
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            advisor = OpenAIAdvisor(api_key='test-key')
            response = advisor.ask(sample_core_output, "Test question")
            
            assert "OpenAI advisory response" in response
            assert mock_client.chat.completions.create.called
    
    def test_ollama_adapter_interface(self, sample_core_output):
        """Test Ollama adapter interface (without actual API call)."""
        from preapply.ai.ollama import OllamaAdvisor
        
        # Mock the availability check and API call
        with patch.object(OllamaAdvisor, '_check_ollama_available'), \
             patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"response": "Ollama advisory response"}
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response
            
            advisor = OllamaAdvisor()
            
            # Test interface
            assert isinstance(advisor, AIAdvisor)
            assert hasattr(advisor, 'ask')
            assert hasattr(advisor, 'is_available')
            
            # Test that ask method exists and can be called (mocked)
            response = advisor.ask(sample_core_output, "Test question")
            assert "Ollama advisory response" in response
            assert mock_post.called


class TestAIDisabled:
    """Test AI disabled behavior."""
    
    def test_ai_disabled_returns_none(self):
        """Test that provider='none' returns None."""
        from preapply.cli.commands.ask import _get_ai_advisor
        
        advisor = _get_ai_advisor("none")
        assert advisor is None
    
    def test_ai_disabled_shows_deterministic_explanation(self, sample_core_output, capsys):
        """Test that AI disabled shows deterministic explanation only."""
        from preapply.presentation.explainer import explain_overall_with_id
        
        explanation, explanation_id = explain_overall_with_id(sample_core_output)
        
        # When AI is disabled, should show deterministic explanation
        assert explanation is not None
        assert explanation_id is not None
        assert len(explanation) > 0


class TestCoreOutputImmutability:
    """Test that CoreOutput is never modified by AI."""
    
    def test_core_output_immutability_after_prompt(self, sample_core_output):
        """CoreOutput must remain unchanged after prompt construction."""
        original_dict = sample_core_output.model_dump()
        
        # Build prompt (should not modify CoreOutput)
        from preapply.ai.prompt import build_prompt
        build_prompt(sample_core_output, "Test question")
        
        # Verify CoreOutput unchanged
        assert sample_core_output.model_dump() == original_dict
    
    def test_core_output_immutability_after_ai_call(self, sample_core_output):
        """CoreOutput must remain unchanged after AI call."""
        original_risk_level = sample_core_output.risk_level
        original_score = sample_core_output.blast_radius_score
        original_dict = sample_core_output.model_dump()
        
        # Mock AI advisor (doesn't modify, just reads)
        class MockAdvisor(AIAdvisor):
            def ask(self, core_output, question, max_tokens=None):
                # AI only reads CoreOutput, never modifies
                _ = core_output.risk_level  # Read only
                _ = core_output.blast_radius_score  # Read only
                return "Response"
            
            def is_available(self):
                return True
        
        advisor = MockAdvisor()
        
        # Call AI (should not modify CoreOutput)
        advisor.ask(sample_core_output, "Test")
        
        # Verify CoreOutput unchanged
        assert sample_core_output.risk_level == original_risk_level
        assert sample_core_output.blast_radius_score == original_score
        assert sample_core_output.model_dump() == original_dict
