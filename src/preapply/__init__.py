"""PreApply - Deterministic infrastructure risk analysis engine."""

from typing import Dict, Any
from pydantic import ValidationError
from .ingest.plan_loader import load_plan_json
from .ingest.plan_normalizer import normalize_plan
from .graph.dependency_graph import DependencyGraph
from .analysis.risk_scoring import calculate_risk_score
from .analysis.recommendations import generate_recommendations
from .contracts.core_output import CoreOutput, RiskLevel
from .config import load_scoring_config
from .utils.logging import setup_logging, get_logger
from .utils.errors import PreApplyError

__version__ = "0.1.0"

__all__ = ["analyze"]

setup_logging()
logger = get_logger("preapply")


def analyze(plan_json_path: str, config_path: str = None, format_human: bool = False) -> Dict[str, Any]:
    """Analyze Terraform plan and return risk assessment."""
    try:
        logger.info(f"Starting analysis of plan: {plan_json_path}")
        
        config = load_scoring_config(config_path)
        plan_data = load_plan_json(plan_json_path)
        normalized_plan = normalize_plan(plan_data)
        
        if not normalized_plan.resources:
            logger.warning("No resources found in plan")
            return _create_empty_output()
        
        graph = DependencyGraph()
        graph.build_from_resources(normalized_plan.resources)
        risk_score = calculate_risk_score(graph, config)
        recommendations = generate_recommendations(graph, risk_score, config)
        
        try:
            output = CoreOutput(
                version="1.0.0",
                risk_level=RiskLevel(risk_score["risk_level"]),
                blast_radius_score=risk_score["blast_radius_score"],
                affected_components=risk_score.get("affected_components", []),
                affected_count=risk_score.get("affected_count", 0),
                risk_attributes=risk_score.get("risk_attributes"),
                risk_factors=risk_score.get("contributing_factors", []),
                recommendations=recommendations
            )
        except ValidationError as e:
            raise
        
        logger.info(f"Analysis complete: {output.risk_level} risk (score: {output.blast_radius_score})")
        
        if format_human:
            from .presentation.human_formatter import format_human_friendly
            return {"formatted": format_human_friendly(output), "structured": output.model_dump()}
        
        return output.model_dump()
        
    except PreApplyError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during analysis: {e}", exc_info=True)
        raise PreApplyError(f"Analysis failed: {e}") from e


def _create_empty_output() -> Dict[str, Any]:
    """Create empty output for plans with no changes."""
    from .contracts.risk_attributes import RiskAttributes, BlastRadiusMetrics
    output = CoreOutput(
        version="1.0.0",
        risk_level=RiskLevel.LOW,
        blast_radius_score=0,
        affected_components=[],
        affected_count=0,
        risk_attributes=RiskAttributes(
            blast_radius=BlastRadiusMetrics(
                affected_resources=0,
                affected_components=0,
                changed_resources=0
            )
        ),
        risk_factors=[],
        recommendations=[]
    )
    return output.model_dump()
