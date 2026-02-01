"""Tests for GitHub PR comment formatting and posting."""

import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest
from preapply.contracts.core_output import CoreOutput
from preapply.report.github import format_github_comment, post_pr_comment, COMMENT_MARKER


@pytest.fixture
def sample_core_output():
    """Load sample CoreOutput from fixture."""
    fixture_path = Path(__file__).parent / "fixtures" / "core_output.sample.json"
    with open(fixture_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return CoreOutput(**data)


class TestDeterminism:
    """Test that same CoreOutput produces same GitHub comment."""
    
    def test_github_comment_determinism(self, sample_core_output):
        """Same CoreOutput → same comment string."""
        comment1 = format_github_comment(sample_core_output)
        comment2 = format_github_comment(sample_core_output)
        
        assert comment1 == comment2, "GitHub comment must be deterministic"
    
    def test_github_comment_contains_marker(self, sample_core_output):
        """Comment must contain PreApply marker."""
        comment = format_github_comment(sample_core_output)
        assert COMMENT_MARKER in comment, "Comment must contain PreApply marker"
    
    def test_github_comment_structure(self, sample_core_output):
        """Comment must have expected structure."""
        comment = format_github_comment(sample_core_output)
        
        # Must contain key sections
        assert "## PreApply Risk Assessment" in comment
        assert "**Risk Level:**" in comment
        assert "**Blast Radius:**" in comment
        assert "<details>" in comment
        assert "Deterministic Explanation" in comment


class TestGitHubAPIContract:
    """Test GitHub API integration contract (mocked)."""
    
    @patch('preapply.report.github.requests.post')
    @patch('preapply.report.github.requests.get')
    def test_post_comment_calls_correct_endpoint(self, mock_get, mock_post, sample_core_output):
        """Test that POST request uses correct GitHub API endpoint."""
        mock_post.return_value = Mock(status_code=201)
        mock_post.return_value.raise_for_status = Mock()
        
        comment = format_github_comment(sample_core_output)
        post_pr_comment("owner/repo", 123, comment, "test_token")
        
        # Verify POST was called
        assert mock_post.called, "POST request must be made"
        
        # Verify endpoint
        call_args = mock_post.call_args
        assert "api.github.com/repos/owner/repo/issues/123/comments" in call_args[0][0]
    
    @patch('preapply.report.github.requests.post')
    @patch('preapply.report.github.requests.get')
    def test_post_comment_includes_auth_header(self, mock_get, mock_post, sample_core_output):
        """Test that request includes Authorization header."""
        mock_post.return_value = Mock(status_code=201)
        mock_post.return_value.raise_for_status = Mock()
        
        comment = format_github_comment(sample_core_output)
        post_pr_comment("owner/repo", 123, comment, "test_token_123")
        
        # Verify headers
        call_kwargs = mock_post.call_args[1]
        headers = call_kwargs.get('headers', {})
        
        assert 'Authorization' in headers, "Authorization header must be present"
        assert headers['Authorization'] == "token test_token_123", "Token must be in header"
    
    @patch('preapply.report.github.requests.post')
    @patch('preapply.report.github.requests.get')
    def test_post_comment_includes_marker(self, mock_get, mock_post, sample_core_output):
        """Test that posted comment contains PreApply marker."""
        mock_post.return_value = Mock(status_code=201)
        mock_post.return_value.raise_for_status = Mock()
        
        comment = format_github_comment(sample_core_output)
        post_pr_comment("owner/repo", 123, comment, "test_token")
        
        # Verify comment body contains marker
        call_kwargs = mock_post.call_args[1]
        body = call_kwargs.get('json', {}).get('body', '')
        
        assert COMMENT_MARKER in body, "Posted comment must contain PreApply marker"
    
    @patch('preapply.report.github.requests.patch')
    @patch('preapply.report.github.requests.post')
    @patch('preapply.report.github.requests.get')
    def test_update_existing_comment(self, mock_get, mock_post, mock_patch, sample_core_output):
        """Test that --update flag updates existing comment."""
        # Mock GET to return existing comment
        existing_comment = {
            "id": 456,
            "body": f"{COMMENT_MARKER}\nOld comment"
        }
        mock_get.return_value = Mock(status_code=200, json=lambda: [existing_comment])
        mock_get.return_value.raise_for_status = Mock()
        
        # Mock PATCH for update
        mock_patch.return_value = Mock(status_code=200)
        mock_patch.return_value.raise_for_status = Mock()
        
        comment = format_github_comment(sample_core_output)
        post_pr_comment("owner/repo", 123, comment, "test_token", update=True)
        
        # Verify PATCH was called, not POST
        assert mock_patch.called, "PATCH must be called for update"
        assert not mock_post.called, "POST must not be called when updating"
        
        # Verify PATCH endpoint
        patch_url = mock_patch.call_args[0][0]
        assert "api.github.com/repos/owner/repo/issues/comments/456" in patch_url
