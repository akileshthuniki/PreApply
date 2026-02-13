"""CI/CD artifact generation from CoreOutput."""

import json
from datetime import datetime, timezone
from pathlib import Path
from ..contracts.core_output import CoreOutput
from ..presentation.explainer import explain_overall_with_id
from ..utils.errors import PreApplyError
from ..utils.logging import get_logger

logger = get_logger("report.artifact")

# Package version (from pyproject.toml)
PACKAGE_VERSION = "0.1.1"


def generate_artifacts(core_output: CoreOutput, output_dir: Path) -> None:
    """
    Generate CI/CD artifacts from CoreOutput.
    
    Creates the following files in output_dir:
    - core_output.json: Full CoreOutput (exact copy)
    - summary.json: High-level summary
    - risk_attributes.json: Structured risk attributes
    - metadata.json: Report metadata
    
    Args:
        core_output: CoreOutput from analysis
        output_dir: Directory to write artifacts to
        
    Raises:
        PreApplyError: If file write fails
    """
    # Create output directory
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise PreApplyError(f"Failed to create output directory: {e}")
    
    # Get explanation for summary
    explanation, explanation_id = explain_overall_with_id(core_output)
    
    # 1. core_output.json - Exact copy of CoreOutput
    core_output_path = output_dir / "core_output.json"
    try:
        with open(core_output_path, 'w', encoding='utf-8') as f:
            json.dump(core_output.model_dump(), f, indent=2, default=str)
        logger.debug(f"Written core_output.json: {core_output_path}")
    except (OSError, TypeError) as e:
        raise PreApplyError(f"Failed to write core_output.json: {e}")
    
    # 2. summary.json - High-level summary
    summary = {
        "risk_level": str(core_output.risk_level),
        "blast_radius_score": core_output.blast_radius_score,
        "affected_count": core_output.affected_count,
        "affected_components_count": len(core_output.affected_components),
        "explanation_id": explanation_id.value if hasattr(explanation_id, 'value') else str(explanation_id),
        "explanation_preview": explanation[:200] if explanation else ""
    }
    
    summary_path = output_dir / "summary.json"
    try:
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        logger.debug(f"Written summary.json: {summary_path}")
    except OSError as e:
        raise PreApplyError(f"Failed to write summary.json: {e}")
    
    # 3. risk_attributes.json - Structured risk attributes
    risk_attrs_path = output_dir / "risk_attributes.json"
    try:
        with open(risk_attrs_path, 'w', encoding='utf-8') as f:
            json.dump(core_output.risk_attributes.model_dump(), f, indent=2, default=str)
        logger.debug(f"Written risk_attributes.json: {risk_attrs_path}")
    except (OSError, TypeError) as e:
        raise PreApplyError(f"Failed to write risk_attributes.json: {e}")
    
    # 4. metadata.json - Report metadata
    metadata = {
        "preapply_version": PACKAGE_VERSION,
        "core_output_version": core_output.version,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator": "preapply report artifact"
    }
    
    metadata_path = output_dir / "metadata.json"
    try:
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        logger.debug(f"Written metadata.json: {metadata_path}")
    except OSError as e:
        raise PreApplyError(f"Failed to write metadata.json: {e}")
    
    logger.info(f"Generated artifacts in: {output_dir}")
