"""Tests for markdown report generation."""

import json
from pathlib import Path
import tempfile
import pytest
from preapply.contracts.core_output import CoreOutput
from preapply.report.markdown import generate_markdown


@pytest.fixture
def sample_core_output():
    """Load sample CoreOutput from fixture."""
    fixture_path = Path(__file__).parent / "fixtures" / "core_output.sample.json"
    with open(fixture_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return CoreOutput(**data)


class TestDeterminism:
    """Test that same CoreOutput produces same markdown report."""
    
    def test_markdown_determinism(self, sample_core_output):
        """Same CoreOutput → same markdown file content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path1 = Path(tmpdir) / "report1.md"
            output_path2 = Path(tmpdir) / "report2.md"
            
            # Generate twice
            generate_markdown(sample_core_output, output_path1)
            generate_markdown(sample_core_output, output_path2)
            
            # Read both files
            content1 = output_path1.read_text(encoding='utf-8')
            content2 = output_path2.read_text(encoding='utf-8')
            
            assert content1 == content2, "Markdown reports must be identical"
    
    def test_markdown_structure(self, sample_core_output):
        """Markdown report must have expected structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.md"
            generate_markdown(sample_core_output, output_path)
            
            content = output_path.read_text(encoding='utf-8')
            
            # Must contain key sections
            assert "# PreApply Risk Assessment Report" in content
            assert "## Summary" in content
            assert "## Risk Attributes" in content
            assert "## Deterministic Explanation" in content
            assert "**Risk Level:**" in content
            assert "**Blast Radius Score:**" in content
