"""Human-friendly output formatter - converts structured data to readable text."""

from typing import List, Dict, Any
from ..contracts.core_output import CoreOutput, RiskLevel
from ..contracts.risk_attributes import SharedDependency


def format_human_friendly(output: CoreOutput) -> str:
    """Format CoreOutput as engineer-grade text report."""
    lines = []
    
    lines.append("PreApply Risk Assessment")
    lines.append("─" * 40)
    lines.append("")
    
    risk_level = output.risk_level
    if isinstance(risk_level, str):
        risk_level = RiskLevel(risk_level)
    lines.append(f"Overall Risk: {risk_level.value}")
    lines.append(f"Blast Radius Score: {output.blast_radius_score} / 100")
    lines.append("")
    
    attrs = output.risk_attributes
    lines.append("Summary")
    lines.append(f"- Resources changed: {attrs.blast_radius.affected_resources}")
    lines.append(f"- Component types affected: {attrs.blast_radius.affected_components}")
    lines.append(f"- Shared dependencies impacted: {len(attrs.shared_dependencies)}")
    lines.append(f"- Critical infrastructure impacted: {len(attrs.critical_infrastructure)}")
    lines.append("")
    
    critical_risks = _categorize_risks(attrs)
    all_high_risk = []
    
    for risk in critical_risks["critical"]:
        all_high_risk.append({
            "resource_id": risk.resource_id,
            "resource_type": risk.resource_type,
            "dependents": risk.dependents,
            "is_critical": risk.is_critical,
            "is_shared": True,
            "risk_reason": risk.risk_reason
        })
    
    for critical in attrs.critical_infrastructure:
        all_high_risk.append({
            "resource_id": critical.resource_id,
            "resource_type": critical.resource_type,
            "dependents": None,
            "is_critical": True,
            "is_shared": False,
            "risk_reason": critical.risk_reason
        })
    
    if all_high_risk:
        lines.append("High-Risk Change Drivers")
        for idx, risk in enumerate(all_high_risk, 1):
            lines.extend(_format_high_risk_driver(idx, risk, attrs))
            lines.append("")
    
    if critical_risks["secondary"]:
        lines.append("Secondary Risk Factors")
        for risk in critical_risks["secondary"]:
            resource_name = risk.resource_id.split('.')[-1]
            lines.append(f"- {risk.resource_type}.{resource_name} ({risk.dependents} dependents)")
        lines.append("")
    
    if len(attrs.shared_dependencies) > 0 or len(attrs.critical_infrastructure) > 0:
        lines.append("Recommendation")
        rec = _generate_recommendation(attrs)
        if rec:
            lines.append(f"- {rec}")
        lines.append("")
    
    lines.append("Next Steps")
    lines.append("- Inspect high-risk resources manually")
    if all_high_risk:
        first_risk = all_high_risk[0]
        lines.append(f"- Run: preapply chat \"Explain risk for {first_risk['resource_id']}\"")
    else:
        lines.append("- Run: preapply chat \"Explain risk assessment\"")
    
    return "\n".join(lines)


def _format_high_risk_driver(index: int, risk: Dict[str, Any], attrs) -> List[str]:
    """Format a high-risk change driver."""
    lines = []
    resource_id = risk["resource_id"]
    dependents = risk["dependents"]
    is_critical = risk["is_critical"]
    is_shared = risk["is_shared"]
    risk_reason = risk.get("risk_reason")
    
    lines.append(f"{index}. {resource_id}")
    
    if dependents is not None:
        lines.append(f"   - Dependents: {dependents}")
    
    classification_parts = []
    if is_shared:
        classification_parts.append("Shared")
    if is_critical:
        classification_parts.append("Critical")
    if classification_parts:
        lines.append(f"   - Classification: {' + '.join(classification_parts)}")
    
    if attrs.action_types:
        lines.append(f"   - Action: {', '.join(attrs.action_types)}")
    
    if risk_reason:
        lines.append(f"   - Risk: {risk_reason}")
    
    return lines


def _generate_recommendation(attrs) -> str:
    """Generate a concise recommendation."""
    if len(attrs.shared_dependencies) > 2:
        return "Consider isolating networking changes from application-layer changes."
    
    if len(attrs.critical_infrastructure) > 0:
        return "Apply and validate shared infrastructure independently."
    
    if len(attrs.shared_dependencies) > 0:
        return "Review shared dependencies before applying changes."
    
    return None


def _categorize_risks(attrs) -> Dict[str, List[SharedDependency]]:
    """Categorize shared dependencies into critical and secondary."""
    critical = []
    secondary = []
    
    for dep in attrs.shared_dependencies:
        if dep.dependents >= 5 or dep.is_critical:
            critical.append(dep)
        else:
            secondary.append(dep)
    
    critical.sort(key=lambda x: x.dependents, reverse=True)
    secondary.sort(key=lambda x: x.dependents, reverse=True)
    
    return {"critical": critical, "secondary": secondary}

