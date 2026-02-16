"""Detect cost spikes and resource scaling in Terraform plan."""

from typing import Dict, Any, List, Optional
from ..contracts.risk_attributes import CostAlert
from ..utils.logging import get_logger

logger = get_logger("analysis.cost_analysis")


def _parse_resource_type(address: str) -> str:
    """Extract resource type from Terraform address."""
    parts = address.split(".")
    for p in parts:
        if "_" in p and p not in ("module", "aws", "azurerm", "google"):
            return p
    return ""


def detect_cost_alerts(plan_data: Dict[str, Any], config: Dict[str, Any]) -> List[CostAlert]:
    """
    Detect high-cost resource creation and instance scaling in Terraform plan.

    Checks for:
    - Creation of high-cost types (e.g. aws_nat_gateway)
    - Creation of high-cost instance types
    - Instance scaling (e.g. t3.micro -> p4d.24xlarge)

    Args:
        plan_data: Raw Terraform plan JSON dictionary
        config: PreApply configuration (cost_alerts section)

    Returns:
        List of CostAlert objects
    """
    alerts: List[CostAlert] = []
    cost_config = config.get("cost_alerts", {})
    high_cost_types = set(cost_config.get("high_cost_types", []))
    high_cost_instance_types = set(cost_config.get("high_cost_instance_types", []))
    tiers = cost_config.get("instance_cost_tiers", {})
    low_tier = set(tiers.get("low", []))
    high_tier = set(tiers.get("high", []))

    resource_changes = plan_data.get("resource_changes", [])

    for rc in resource_changes:
        if not isinstance(rc, dict):
            continue
        address = rc.get("address", "")
        change = rc.get("change", {})
        if not change:
            continue

        resource_type = _parse_resource_type(address)
        if not resource_type:
            continue

        actions = change.get("actions", [])
        before = change.get("before") or {}
        after = change.get("after") or {}

        # High-cost type creation
        if "create" in actions and resource_type in high_cost_types:
            alerts.append(CostAlert(
                resource_id=address,
                resource_type=resource_type,
                reason="high_cost_creation",
                alert_type="HIGH_COST_CREATION"
            ))

        # Instance type checks (aws_instance, aws_db_instance, etc.)
        if resource_type in ("aws_instance", "aws_db_instance", "aws_launch_template"):
            instance_type_before = (before.get("instance_type") or "").strip()
            instance_type_after = (after.get("instance_type") or "").strip()

            if "create" in actions and instance_type_after in high_cost_instance_types:
                alerts.append(CostAlert(
                    resource_id=address,
                    resource_type=resource_type,
                    reason="high_cost_creation",
                    alert_type="HIGH_COST_CREATION"
                ))
            elif "update" in actions or "replace" in actions:
                # Scaling: low -> high tier
                if instance_type_before in low_tier and instance_type_after in high_tier:
                    alerts.append(CostAlert(
                        resource_id=address,
                        resource_type=resource_type,
                        reason=f"instance_scaling ({instance_type_before} -> {instance_type_after})",
                        alert_type="INSTANCE_SCALING"
                    ))
                elif instance_type_after in high_cost_instance_types and instance_type_before != instance_type_after:
                    alerts.append(CostAlert(
                        resource_id=address,
                        resource_type=resource_type,
                        reason=f"instance_scaling ({instance_type_before or 'unknown'} -> {instance_type_after})",
                        alert_type="INSTANCE_SCALING"
                    ))

    if alerts:
        logger.info(f"Detected {len(alerts)} cost alert(s)")
    return alerts
