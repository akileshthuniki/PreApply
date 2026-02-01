"""Markdown report generation from CoreOutput."""

from pathlib import Path
from ..contracts.core_output import CoreOutput
from ..presentation.explainer import explain_overall_with_id
from ..utils.errors import PreApplyError
from ..utils.logging import get_logger

logger = get_logger("report.markdown")


def generate_markdown(core_output: CoreOutput, output_path: Path) -> None:
    """
    Generate markdown report from CoreOutput.
    
    Args:
        core_output: CoreOutput from analysis
        output_path: Path to output markdown file
        
    Raises:
        PreApplyError: If file write fails
    """
    # Get explanation with ID
    explanation, explanation_id = explain_overall_with_id(core_output)
    
    attrs = core_output.risk_attributes
    
    # Build markdown sections
    sections = []
    
    # Title
    sections.append("# PreApply Risk Assessment Report")
    sections.append("")
    
    # Summary
    sections.append("## Summary")
    sections.append("")
    sections.append(f"- **Risk Level:** {core_output.risk_level}")
    sections.append(f"- **Blast Radius Score:** {core_output.blast_radius_score}/100")
    sections.append(f"- **Affected Resources:** {core_output.affected_count}")
    sections.append(f"- **Affected Components:** {len(core_output.affected_components)}")
    sections.append("")
    
    # Risk Attributes
    sections.append("## Risk Attributes")
    sections.append("")
    
    # Blast Radius Metrics
    sections.append("### Blast Radius Metrics")
    sections.append("")
    sections.append(f"- **Affected Resources:** {attrs.blast_radius.affected_resources}")
    sections.append(f"- **Affected Components:** {attrs.blast_radius.affected_components}")
    sections.append(f"- **Changed Resources:** {attrs.blast_radius.changed_resources}")
    sections.append("")
    
    # Shared Dependencies
    if attrs.shared_dependencies:
        sections.append("### Shared Dependencies")
        sections.append("")
        for dep in attrs.shared_dependencies:
            sections.append(f"- **{dep.resource_type}** (`{dep.resource_id}`)")
            sections.append(f"  - Dependents: {dep.dependents}")
            sections.append(f"  - Critical: {dep.is_critical}")
            if dep.multiplier_applied:
                sections.append(f"  - Multiplier Applied: {dep.multiplier_applied}")
            sections.append(f"  - Risk Reason: {dep.risk_reason}")
            sections.append("")
    else:
        sections.append("### Shared Dependencies")
        sections.append("")
        sections.append("None detected.")
        sections.append("")
    
    # Critical Infrastructure
    if attrs.critical_infrastructure:
        sections.append("### Critical Infrastructure")
        sections.append("")
        for crit in attrs.critical_infrastructure:
            sections.append(f"- **{crit.resource_type}** (`{crit.resource_id}`)")
            sections.append(f"  - Risk Reason: {crit.risk_reason}")
            sections.append("")
    else:
        sections.append("### Critical Infrastructure")
        sections.append("")
        sections.append("None detected.")
        sections.append("")
    
    # Action Types
    sections.append("### Action Types")
    sections.append("")
    if attrs.action_types:
        for action_type in attrs.action_types:
            sections.append(f"- `{action_type}`")
    else:
        sections.append("None detected.")
    sections.append("")
    
    if attrs.action_multiplier:
        sections.append(f"**Action Multiplier Applied:** {attrs.action_multiplier}")
        sections.append("")
    
    # Deterministic Explanation
    sections.append("## Deterministic Explanation")
    sections.append("")
    sections.append(f"**Explanation ID:** `{explanation_id.value if hasattr(explanation_id, 'value') else explanation_id}`")
    sections.append("")
    sections.append(explanation)
    sections.append("")
    
    # Recommendations
    if core_output.recommendations:
        sections.append("## Recommendations")
        sections.append("")
        for rec in core_output.recommendations:
            sections.append(f"- {rec}")
        sections.append("")
    
    # Write to file
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(sections))
        logger.info(f"Generated markdown report: {output_path}")
    
    except OSError as e:
        raise PreApplyError(f"Failed to write markdown report: {e}")
