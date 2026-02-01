"""Tests for plan loader."""

import json
import tempfile
from pathlib import Path
import pytest
from preapply.ingest.plan_loader import load_plan_json
from preapply.utils.errors import PlanLoadError


class TestPlanLoader:
    """Test plan JSON loading."""
    
    def test_load_valid_plan(self):
        """Test loading a valid Terraform plan JSON."""
        plan_data = {
            "format_version": "1.0",
            "resource_changes": [
                {
                    "address": "aws_lb.test",
                    "change": {"actions": ["create"]}
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(plan_data, f)
            temp_path = f.name
        
        try:
            result = load_plan_json(temp_path)
            assert result == plan_data
            assert "resource_changes" in result
        finally:
            Path(temp_path).unlink()
    
    def test_load_missing_file(self):
        """Test loading non-existent file raises error."""
        with pytest.raises(PlanLoadError, match="Plan file not found"):
            load_plan_json("nonexistent.json")
    
    def test_load_invalid_json(self):
        """Test loading invalid JSON raises error."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json {")
            temp_path = f.name
        
        try:
            with pytest.raises(PlanLoadError, match="Invalid JSON"):
                load_plan_json(temp_path)
        finally:
            Path(temp_path).unlink()
    
    def test_load_missing_resource_changes(self):
        """Test loading plan without resource_changes adds empty list."""
        plan_data = {"format_version": "1.0"}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(plan_data, f)
            temp_path = f.name
        
        try:
            result = load_plan_json(temp_path)
            assert "resource_changes" in result
            assert result["resource_changes"] == []
        finally:
            Path(temp_path).unlink()
