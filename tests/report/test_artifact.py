"""Tests for CI/CD artifact generation."""

import json
import hashlib
from pathlib import Path
import tempfile
from datetime import datetime
import pytest
from preapply.contracts.core_output import CoreOutput
from preapply.report.artifact import generate_artifacts


@pytest.fixture
def sample_core_output():
    """Load sample CoreOutput from fixture."""
    fixture_path = Path(__file__).parent / "fixtures" / "core_output.sample.json"
    with open(fixture_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return CoreOutput(**data)


def _hash_directory(directory: Path, exclude_metadata: bool = False) -> str:
    """Calculate hash of all files in directory (for idempotency test)."""
    hasher = hashlib.sha256()
    for file_path in sorted(directory.rglob('*')):
        if file_path.is_file():
            # Exclude metadata.json from hash if requested (timestamp changes)
            if exclude_metadata and file_path.name == "metadata.json":
                # Hash metadata without timestamp
                metadata = json.loads(file_path.read_text())
                metadata_no_timestamp = {k: v for k, v in metadata.items() if k != "generated_at"}
                hasher.update(json.dumps(metadata_no_timestamp, sort_keys=True).encode())
            else:
                hasher.update(file_path.read_bytes())
            hasher.update(str(file_path.relative_to(directory)).encode())
    return hasher.hexdigest()


class TestDeterminism:
    """Test that same CoreOutput produces same artifacts."""
    
    def test_artifact_determinism(self, sample_core_output):
        """Same CoreOutput → same artifact files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir1 = Path(tmpdir) / "artifacts1"
            output_dir2 = Path(tmpdir) / "artifacts2"
            
            # Generate twice
            generate_artifacts(sample_core_output, output_dir1)
            generate_artifacts(sample_core_output, output_dir2)
            
            # Compare core_output.json (must be byte-identical)
            core1 = output_dir1 / "core_output.json"
            core2 = output_dir2 / "core_output.json"
            
            assert core1.read_bytes() == core2.read_bytes(), "core_output.json must be byte-identical"
            
            # Compare summary.json structure (ignore timestamp in metadata)
            summary1 = json.loads((output_dir1 / "summary.json").read_text())
            summary2 = json.loads((output_dir2 / "summary.json").read_text())
            
            assert summary1 == summary2, "summary.json must be identical (excluding metadata timestamp)"


class TestArtifactIntegrity:
    """Test that all required artifact files are generated correctly."""
    
    def test_all_four_files_exist(self, sample_core_output):
        """All 4 artifact files must exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "artifacts"
            generate_artifacts(sample_core_output, output_dir)
            
            required_files = [
                "core_output.json",
                "summary.json",
                "risk_attributes.json",
                "metadata.json"
            ]
            
            for filename in required_files:
                file_path = output_dir / filename
                assert file_path.exists(), f"{filename} must exist"
                assert file_path.is_file(), f"{filename} must be a file"
    
    def test_core_output_byte_identical(self, sample_core_output):
        """core_output.json must be byte-identical to original CoreOutput."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "artifacts"
            generate_artifacts(sample_core_output, output_dir)
            
            # Load generated core_output.json
            generated_path = output_dir / "core_output.json"
            generated_data = json.loads(generated_path.read_text())
            
            # Convert sample to dict (excluding Pydantic metadata)
            original_dict = sample_core_output.model_dump()
            
            # Compare (using model_dump to ensure same structure)
            assert generated_data == original_dict, "core_output.json must match original CoreOutput"
    
    def test_metadata_contains_timestamp_and_version(self, sample_core_output):
        """metadata.json must contain timestamp and version."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "artifacts"
            generate_artifacts(sample_core_output, output_dir)
            
            metadata_path = output_dir / "metadata.json"
            metadata = json.loads(metadata_path.read_text())
            
            # Must have required fields
            assert "preapply_version" in metadata, "metadata must contain preapply_version"
            assert "core_output_version" in metadata, "metadata must contain core_output_version"
            assert "generated_at" in metadata, "metadata must contain generated_at"
            assert "generator" in metadata, "metadata must contain generator"
            
            # Verify timestamp is valid ISO8601
            try:
                datetime.fromisoformat(metadata["generated_at"].replace('Z', '+00:00'))
            except ValueError:
                pytest.fail(f"generated_at must be valid ISO8601: {metadata['generated_at']}")
            
            # Verify versions are strings
            assert isinstance(metadata["preapply_version"], str), "preapply_version must be string"
            assert isinstance(metadata["core_output_version"], str), "core_output_version must be string"


class TestIdempotency:
    """Test that running artifact generation twice produces identical output."""
    
    def test_idempotency_directory_hash(self, sample_core_output):
        """Run twice → directory hash must match (excluding metadata timestamp)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "artifacts"
            
            # First run
            generate_artifacts(sample_core_output, output_dir)
            hash1 = _hash_directory(output_dir, exclude_metadata=True)
            
            # Second run (clear and regenerate)
            import shutil
            shutil.rmtree(output_dir)
            output_dir.mkdir()
            generate_artifacts(sample_core_output, output_dir)
            hash2 = _hash_directory(output_dir, exclude_metadata=True)
            
            # Hashes must match (proves idempotency, excluding timestamp)
            assert hash1 == hash2, "Directory hash must be identical on second run (idempotency, excluding timestamp)"
    
    def test_idempotency_core_output_identical(self, sample_core_output):
        """Run twice → core_output.json must be byte-identical."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "artifacts"
            
            # First run
            generate_artifacts(sample_core_output, output_dir)
            core1_bytes = (output_dir / "core_output.json").read_bytes()
            
            # Second run (clear and regenerate)
            import shutil
            shutil.rmtree(output_dir)
            output_dir.mkdir()
            generate_artifacts(sample_core_output, output_dir)
            core2_bytes = (output_dir / "core_output.json").read_bytes()
            
            # Must be byte-identical
            assert core1_bytes == core2_bytes, "core_output.json must be byte-identical on second run"
