"""Human-friendly output formatter - converts structured data to readable text."""

import math
import os
from typing import List, Dict, Any, Optional
from ..contracts.core_output import CoreOutput, RiskLevel
from ..contracts.risk_attributes import (
    SharedDependency,
    SensitiveDeletion,
    SecurityExposure,
    CostAlert,
)

def _use_ascii(ascii_mode: Optional[bool] = None) -> bool:
    """Resolve whether to use ASCII output (checked at format time)."""
    if ascii_mode is not None:
        return bool(ascii_mode)
    return os.environ.get("PREAPPLY_ASCII", "").lower() in ("1", "true", "yes")


def _box(title: str, width: int = 65, ascii_mode: bool = False) -> List[str]:
    """Return box-drawing header lines."""
    b = {"tl": "+", "tr": "+", "h": "-", "v": "|"} if ascii_mode else {"tl": "\u250c", "tr": "\u2510", "h": "\u2500", "v": "\u2502"}
    h = b["h"] * (width - 2)
    return [
        b["tl"] + h + b["tr"],
        f"{b['v']} {title:<{width - 4}} {b['v']}",
        ("+" if ascii_mode else "\u2514") + h + ("+" if ascii_mode else "\u2518"),
        "",
    ]


def _alert_banner(level: str, message: str, width: int = 65, ascii_mode: bool = False) -> List[str]:
    """Return double-line alert banner."""
    emoji_map = {
        "CRITICAL-CATASTROPHIC": "[!] " if ascii_mode else "\u26a0\ufe0f ",
        "CRITICAL": "[!] " if ascii_mode else "\u26a0\ufe0f ",
        "HIGH-SEVERE": "[!] " if ascii_mode else "\u26a0\ufe0f  ",
        "HIGH": "[!] " if ascii_mode else "\u26a0\ufe0f  ",
        "MEDIUM": "[i] " if ascii_mode else "\u2139\ufe0f  ",
        "LOW": "[OK] " if ascii_mode else "\u2705 ",
    }
    emoji = emoji_map.get(level, "")
    text = f"{emoji}{message}"
    if ascii_mode:
        h = "=" * (width - 2)
        return ["+" + h + "+", f"| {text:<{width - 4}} |", "+" + h + "+", ""]
    return [
        "\u2554" + "\u2550" * (width - 2) + "\u2557",
        f"\u2551 {text:<{width - 4}} \u2551",
        "\u255a" + "\u2550" * (width - 2) + "\u255d",
        "",
    ]


def _section(title: str, width: int = 65, ascii_mode: bool = False) -> List[str]:
    """Return section divider."""
    h = "-" * width
    return [h, title.center(width), h]


def _dimension_thresholds() -> Dict[str, float]:
    """Thresholds per dimension (matches risk_scoring config)."""
    return {
        "data": 40.0,
        "security": 40.0,
        "infrastructure": 60.0,
        "cost": 30.0,
    }


def _dimension_status(score: float, threshold: float) -> str:
    """Status label for a dimension score."""
    if score <= 0:
        return "OK"
    if score >= threshold * 1.5:
        return "SEVERE"
    if score >= threshold:
        return "HIGH"
    if score >= threshold * 0.5:
        return "MODERATE"
    return "OK"


def _dimension_label(dim: str) -> str:
    """Human label for dimension."""
    return {"data": "Data Loss", "security": "Security", "infrastructure": "Infrastructure", "cost": "Cost"}.get(
        dim, dim.title()
    )


def _build_why_section(
    detailed: str,
    attrs,
    breakdown,
    ascii_mode: bool = False,
) -> List[str]:
    """Build WHY THIS IS [LEVEL] section."""
    b = "*" if ascii_mode else "\u2022"
    lines = []
    thresholds = _dimension_thresholds()
    dims = breakdown.dimensions if breakdown else {}

    elevated = [(d, s) for d, s in dims.items() if s >= thresholds.get(d, 0)]
    elevated_labels = [d for d, _ in elevated]

    if len(elevated) >= 2:
        lines.append(f"{b} Multiple critical dimensions simultaneously elevated ({', '.join(elevated_labels)})")
    if breakdown and breakdown.interaction_multiplier > 1.0:
        mult_str = f"{breakdown.interaction_multiplier:.2f}x"
        lines.append(f"{b} Interaction multiplier: {mult_str} (risks amplify each other)")
    if "data" in elevated_labels and ("security" in elevated_labels or "infrastructure" in elevated_labels):
        lines.append(f"{b} Perfect storm: data loss + security/infrastructure")
    if attrs.sensitive_deletions and (attrs.shared_dependencies or attrs.critical_infrastructure):
        lines.append(f"{b} Production database deletion + shared infra changes")
    if attrs.sensitive_deletions:
        for sd in attrs.sensitive_deletions:
            lines.append(f"{b} Sensitive deletion: {sd.resource_id} ({sd.resource_type})")
    if not lines:
        lines.append(f"{b} Review the risk breakdown and critical items below")
    return lines


def _build_impact_summary(output: CoreOutput, attrs) -> List[str]:
    """Build IMPACT SUMMARY section."""
    br = attrs.blast_radius
    deletions = getattr(output, "deletion_count", 0)
    shared_count = len(attrs.shared_dependencies) + len(attrs.critical_infrastructure)

    log_scale = round(10 * math.log2(br.affected_resources + 1), 1) if br.affected_resources > 0 else 0
    radius_label = "High" if log_scale >= 40 else "Medium" if log_scale >= 20 else "Low"

    return [
        f"Changed:           {br.changed_resources} resources ({deletions} deletion{'s' if deletions != 1 else ''})",
        f"Downstream impact: {br.affected_resources} resources affected",
        f"Blast radius:      {radius_label} (log scale: {log_scale})",
        f"Components:        {br.affected_components} types touched",
        f"Shared resources:  {shared_count} critical infrastructure piece{'s' if shared_count != 1 else ''}",
    ]


def _build_risk_breakdown(attrs, ascii_mode: bool = False) -> List[str]:
    """Build RISK BREAKDOWN BY DIMENSION section."""
    bullet = "*" if ascii_mode else "\u2022"
    lines = []
    if not attrs.risk_breakdown or not attrs.risk_breakdown.dimensions:
        return lines

    rb = attrs.risk_breakdown
    thresholds = _dimension_thresholds()
    dim_order = ["data", "security", "infrastructure", "cost"]

    primary_dim = rb.primary_dimension
    for dim in dim_order:
        score = rb.dimensions.get(dim, 0)
        if score is None or score < 0:
            continue
        th = thresholds.get(dim, 30)
        status = _dimension_status(score, th)
        label = _dimension_label(dim)
        tier = ""
        if dim == primary_dim and score >= th:
            tier = " [PRIMARY RISK - HIGH]"
        elif score >= th:
            tier = " [ELEVATED]"
        elif score > 0:
            tier = " [MODERATE]"

        lines.append(f"{bullet} {label:<16} {score:>6.1f}  {tier}")
        lines.append(f"                          Threshold: {th}, Status: {status}")

    lines.append("")
    lines.append(f"Primary Risk Driver: {_dimension_label(rb.primary_dimension)} ({rb.primary_score:.1f} points)")

    contributing = []
    for d, s in rb.dimensions.items():
        if d != rb.primary_dimension and s >= thresholds.get(d, 0):
            contributing.append(_dimension_label(d))
    if contributing:
        lines.append(f"Contributing Factors: {', '.join(contributing)}")

    return lines


def _format_tree_item(prefix: str, label: str, value: str, ascii_mode: bool = False) -> str:
    """Format a tree line (|- or \\- in ASCII)."""
    return f"    {prefix} {label}: {value}"


def _format_critical_risks(attrs, ascii_mode: bool = False) -> List[str]:
    """Build CRITICAL RISKS section (data loss + shared infra)."""
    branch, last = ("|-", "\\-") if ascii_mode else ("\u251c\u2500", "\u2514\u2500")
    bullet = "*" if ascii_mode else "\u2022"
    lines = []

    if attrs.sensitive_deletions:
        lines.append("DATA LOSS:")
        for sd in attrs.sensitive_deletions:
            lines.append(f"  {bullet} {sd.resource_id}")
            lines.append(_format_tree_item(branch, "Action", "DELETE", ascii_mode))
            lines.append(_format_tree_item(branch, "Type", f"{sd.resource_type} (sensitive)", ascii_mode))
            lines.append(_format_tree_item(branch, "Impact", "Permanent data loss", ascii_mode))
            lines.append(_format_tree_item(last, "Recommendation", "Backup verification required", ascii_mode))
        lines.append("")

    critical_deps = [d for d in attrs.shared_dependencies if d.dependents >= 5 or d.is_critical]
    for ci in attrs.critical_infrastructure:
        critical_deps.append(ci)

    if critical_deps:
        lines.append("SHARED INFRASTRUCTURE:")
        for dep in critical_deps:
            res_id = dep.resource_id if hasattr(dep, "resource_id") else getattr(dep, "resource_id", "?")
            res_type = dep.resource_type if hasattr(dep, "resource_type") else getattr(dep, "resource_type", "?")
            dependents = getattr(dep, "dependents", None)
            risk_reason = getattr(dep, "risk_reason", "Critical infrastructure change")

            action = "UPDATE"
            if attrs.action_types:
                action = attrs.action_types[0] if "DELETE" not in attrs.action_types else "DELETE"
            if "DELETE" in attrs.action_types and "UPDATE" in attrs.action_types:
                action = "UPDATE"

            lines.append(f"  {bullet} {res_id}")
            lines.append(_format_tree_item(branch, "Action", action, ascii_mode))
            if dependents is not None:
                lines.append(_format_tree_item(branch, "Used by", f"{dependents} downstream service{'s' if dependents != 1 else ''}", ascii_mode))
            lines.append(_format_tree_item(branch, "Type", f"Critical ({res_type})", ascii_mode))
            lines.append(_format_tree_item(last, "Impact", risk_reason, ascii_mode))
        lines.append("")

    return lines


def _format_high_risks(attrs, ascii_mode: bool = False) -> List[str]:
    """Build HIGH RISKS section (security + cost)."""
    branch, last = ("|-", "\\-") if ascii_mode else ("\u251c\u2500", "\u2514\u2500")
    bullet = "*" if ascii_mode else "\u2022"
    lines = []

    if attrs.security_exposures:
        lines.append("SECURITY EXPOSURES:")
        for se in attrs.security_exposures:
            lines.append(f"  {bullet} {se.resource_id}")
            lines.append(_format_tree_item(branch, "Issue", se.details, ascii_mode))
            if se.port:
                lines.append(_format_tree_item(branch, "Port", f"{se.port} (sensitive)" if se.port_sensitive else str(se.port), ascii_mode))
            lines.append(_format_tree_item(branch, "Severity", "Public access" if se.port_sensitive else "Exposure", ascii_mode))
            lines.append(_format_tree_item(last, "Recommendation", "Restrict to known IPs", ascii_mode))
        lines.append("")

    if attrs.cost_alerts:
        lines.append("COST ALERTS:")
        for ca in attrs.cost_alerts:
            lines.append(f"  {bullet} {ca.resource_id}")
            if "scaling" in ca.reason.lower():
                lines.append(_format_tree_item(branch, "Alert", "Instance tier scaling", ascii_mode))
                if "->" in ca.reason or "\u2192" in ca.reason:
                    change = ca.reason.split("(")[-1].rstrip(")").strip()
                    lines.append(_format_tree_item(branch, "Change", change, ascii_mode))
                else:
                    lines.append(_format_tree_item(branch, "Reason", ca.reason, ascii_mode))
            else:
                lines.append(_format_tree_item(branch, "Alert", "High-cost resource creation", ascii_mode))
                lines.append(_format_tree_item(branch, "Reason", ca.reason, ascii_mode))
            lines.append(_format_tree_item(last, "Recommendation", "Verify necessity / right-size if possible", ascii_mode))
        lines.append("")

    return lines


def _build_recommended_actions(output: CoreOutput, attrs, ascii_mode: bool = False) -> List[str]:
    """Build RECOMMENDED ACTIONS section."""
    branch = "\\-" if ascii_mode else "\u2514\u2500"
    e_stop = "[X] " if ascii_mode else "\u26d4 "
    e_review = "[1] " if ascii_mode else "\u1f4cb "
    e_lock = "[2] " if ascii_mode else "\u1f512 "
    e_split = "[3] " if ascii_mode else "\u1f4e6 "
    e_check = "[4] " if ascii_mode else "\u2705 "
    lines = []
    detailed = getattr(output, "risk_level_detailed", "") or str(output.risk_level)
    action = getattr(output, "risk_action", "")
    recommendations = getattr(output, "recommendations", []) or []

    if detailed in ("CRITICAL-CATASTROPHIC", "CRITICAL") or action == "HARD_BLOCK":
        lines.append(f"1. {e_stop}STOP - Do not proceed with this plan as-is")
        lines.append("")

    if attrs.sensitive_deletions:
        sd = attrs.sensitive_deletions[0]
        lines.append(f"2. {e_review}REVIEW DATABASE DELETION")
        lines.append(f"   {branch} Verify {sd.resource_id} has recent backup")
        lines.append(f"   {branch} Confirm deletion is intentional (not accidental drift)")
        lines.append(f"   {branch} Document business justification")
        lines.append("")

    if attrs.security_exposures:
        lines.append(f"3. {e_lock}ADDRESS SECURITY EXPOSURE")
        for se in attrs.security_exposures[:1]:
            lines.append(f"   {branch} Restrict {se.resource_id} to specific IP ranges")
        lines.append(f"   {branch} Consider using bastion host or VPN instead")
        lines.append("")

    if attrs.shared_dependencies or attrs.critical_infrastructure:
        lines.append(f"4. {e_split}SPLIT THE CHANGE")
        lines.append(f"   {branch} Apply infrastructure updates separately from deletions")
        lines.append(f"   {branch} Test shared load balancer changes in isolation")
        lines.append(f"   {branch} Verify each stage before proceeding")
        lines.append("")

    if action in ("HARD_BLOCK", "SOFT_BLOCK", "REQUIRE_APPROVAL") and getattr(output, "approval_required", "NONE") != "NONE":
        lines.append(f"5. {e_check}GET APPROVALS")
        lines.append(f"   {branch} {output.approval_required} sign-off required")
        if detailed == "CRITICAL-CATASTROPHIC":
            lines.append(f"   {branch} Schedule incident review meeting")
        lines.append(f"   {branch} Document rollback plan")

    return lines


def _build_next_steps(attrs, ascii_mode: bool = False) -> List[str]:
    """Build NEXT STEPS section."""
    lines = []

    focus = None
    if attrs.sensitive_deletions:
        focus = attrs.sensitive_deletions[0].resource_id
    elif attrs.shared_dependencies:
        focus = attrs.shared_dependencies[0].resource_id
    elif attrs.critical_infrastructure:
        focus = attrs.critical_infrastructure[0].resource_id

    bullet = "*" if ascii_mode else "\u2022"
    lines.append(f"{bullet} Ask AI for detailed explanation (requires: pip install 'preapply[ai]', Ollama):")
    if focus:
        lines.append(f'  $ preapply ask ai "Explain risk for {focus}" plan.json')
    else:
        lines.append('  $ preapply ask ai "Explain risk assessment" plan.json')
    lines.append("")
    lines.append(f"{bullet} For questions or escalation: #infrastructure-oncall")

    return lines


def _get_banner_message(detailed: str, action: str) -> str:
    """Get banner message for risk level."""
    messages = {
        "CRITICAL-CATASTROPHIC": "CATASTROPHIC RISK DETECTED - DO NOT APPLY",
        "CRITICAL": "CRITICAL RISK - VP/DIRECTOR APPROVAL REQUIRED",
        "HIGH-SEVERE": "HIGH-SEVERE RISK - ARCHITECT APPROVAL REQUIRED",
        "HIGH": "HIGH RISK - SENIOR ENGINEER APPROVAL REQUIRED",
        "MEDIUM": "MEDIUM RISK - PEER REVIEW RECOMMENDED",
        "LOW": "LOW RISK - SAFE TO PROCEED",
    }
    return messages.get(detailed, f"{detailed} RISK")


def _get_action_label(action: str) -> str:
    """Human-readable action label."""
    labels = {
        "HARD_BLOCK": "HARD BLOCK - VP approval + incident review required",
        "SOFT_BLOCK": "SOFT BLOCK - VP/Director approval required",
        "REQUIRE_APPROVAL": "Obtain approval before applying",
        "REQUIRE_PEER_REVIEW": "Peer review recommended",
        "AUTO_APPROVE": "Safe to apply",
    }
    return labels.get(action, action)


def format_human_friendly(output: CoreOutput, ascii_mode: Optional[bool] = None) -> str:
    """Format CoreOutput as human-friendly, box-drawn report.
    If ascii_mode is True (or PREAPPLY_ASCII=1), use ASCII-only characters for terminals that don't support Unicode.
    """
    ascii_mode = _use_ascii(ascii_mode)
    W = 65
    lines = []

    # Header box
    lines.extend(_box("PreApply Risk Assessment", W, ascii_mode))

    # Alert banner
    detailed = getattr(output, "risk_level_detailed", None) or str(output.risk_level)
    action = getattr(output, "risk_action", "")
    banner_msg = _get_banner_message(detailed, action)
    lines.extend(_alert_banner(detailed, banner_msg, W, ascii_mode))

    # Top summary
    score = output.blast_radius_score
    lines.append(f"Risk Score: {score:.2f} / 250+ ({detailed} tier)")
    lines.append(f"Required Action: {_get_action_label(action)}")
    approval = getattr(output, "approval_required", None)
    if approval and approval != "NONE":
        lines.append(f"Approval Required: {approval}")
    lines.append("")

    attrs = output.risk_attributes
    breakdown = attrs.risk_breakdown

    # WHY section
    why_title = f"WHY THIS IS {detailed.replace('-', ' ')}" if detailed in ("CRITICAL-CATASTROPHIC", "CRITICAL", "HIGH-SEVERE", "HIGH") else "SUMMARY"
    lines.extend(_section(why_title, W, ascii_mode))
    lines.extend(_build_why_section(detailed, attrs, breakdown, ascii_mode))
    lines.append("")

    # IMPACT SUMMARY
    lines.extend(_section("IMPACT SUMMARY", W, ascii_mode))
    lines.extend(_build_impact_summary(output, attrs))
    lines.append("")

    # RISK BREAKDOWN BY DIMENSION
    if breakdown and any(s > 0 for s in breakdown.dimensions.values()):
        lines.extend(_section("RISK BREAKDOWN BY DIMENSION", W, ascii_mode))
        lines.extend(_build_risk_breakdown(attrs, ascii_mode))
        lines.append("")

    # CRITICAL RISKS
    critical_lines = _format_critical_risks(attrs, ascii_mode)
    if critical_lines:
        sect = "[!!] CRITICAL RISKS (Must Address Before Proceeding)" if ascii_mode else "\u26d4 CRITICAL RISKS (Must Address Before Proceeding)"
        lines.extend(_section(sect, W, ascii_mode))
        lines.extend(critical_lines)

    # HIGH RISKS
    high_lines = _format_high_risks(attrs, ascii_mode)
    if high_lines:
        sect = "[!] HIGH RISKS (Review Carefully)" if ascii_mode else "\u26a0\ufe0f  HIGH RISKS (Review Carefully)"
        lines.extend(_section(sect, W, ascii_mode))
        lines.extend(high_lines)

    # RECOMMENDED ACTIONS
    rec_lines = _build_recommended_actions(output, attrs, ascii_mode)
    if rec_lines:
        lines.extend(_section("RECOMMENDED ACTIONS (in order)", W, ascii_mode))
        lines.extend(rec_lines)
        lines.append("")

    # NEXT STEPS
    lines.extend(_section("NEXT STEPS", W, ascii_mode))
    lines.extend(_build_next_steps(attrs, ascii_mode))

    return "\n".join(lines).rstrip() + "\n"
