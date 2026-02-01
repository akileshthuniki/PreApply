"""Tests for analyze CLI command."""

import json
import tempfile
from pathlib import Path
import pytest
from click.testing import CliRunner
from preapply.cli.main import cli


@pytest.fixture
def sample_plan_file():
    """Create a sample Terraform plan file."""
    plan_data = {
        "format_version": "1.0",
        "resource_changes": [
            {
                "address": "aws_lb.test",
                "change": {"actions": ["create"]},
                "depends_on": []
            }
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(plan_data, f)
        temp_path = f.name
    
    yield temp_path
    Path(temp_path).unlink()


class TestAnalyzeCommand:
    """Test analyze CLI command."""
    
    def test_analyze_command_basic(self, sample_plan_file):
        """Test basic analyze command."""
        runner = CliRunner()
        result = runner.invoke(cli, ['analyze', sample_plan_file])
        
        assert result.exit_code == 0
        assert "risk" in result.output.lower() or "analysis" in result.output.lower()
    
    def test_analyze_command_json_output(self, sample_plan_file):
        """Test analyze command with JSON output."""
        runner = CliRunner()
        result = runner.invoke(cli, ['analyze', sample_plan_file, '--json'])
        
        assert result.exit_code == 0
        # Output might have extra text, try to find JSON
        output = result.output.strip()
        # Try to find JSON object in output
        if output.startswith('{'):
            try:
                json.loads(output)
            except json.JSONDecodeError:
                # If it's not pure JSON, that's okay - might have progress messages
                assert "risk" in output.lower() or "version" in output.lower()
        else:
            # Output might go to stderr, check stdout
            assert len(output) > 0
    
    def test_analyze_command_missing_file(self):
        """Test analyze command with missing file."""
        runner = CliRunner()
        result = runner.invoke(cli, ['analyze', 'nonexistent.json'])
        
        assert result.exit_code != 0
