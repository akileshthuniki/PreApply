"""Detect state-destructive updates: removal of deletion protection."""

from typing import Dict, Any, List
from ..utils.logging import get_logger

logger = get_logger("analysis.state_destructive")


def _parse_resource_type(address: str) -> str:
    """Extract resource type from Terraform address."""
    parts = address.split(".")
    for p in parts:
        if "_" in p and p not in ("module", "aws", "azurerm", "google"):
            return p
    return ""


def _is_deletion_protection_disabled(before: Any, after: Any) -> bool:
    """Check if deletion_protection is being disabled (enabled -> disabled)."""
    before_val = before.get("deletion_protection") if isinstance(before, dict) else None
    after_val = after.get("deletion_protection") if isinstance(after, dict) else None

    if before_val is None or after_val is None:
        return False

    before_off = before_val in (False, "false", "disabled")
    after_off = after_val in (False, "false", "disabled")
    before_on = before_val in (True, "true", "enabled")
    after_on = after_val in (True, "true", "enabled")

    return before_on and after_off


def _is_prevent_destroy_disabled(before: Any, after: Any) -> bool:
    """Check if prevent_destroy is being disabled (true -> false)."""
    before_val = before.get("prevent_destroy") if isinstance(before, dict) else None
    after_val = after.get("prevent_destroy") if isinstance(after, dict) else None

    if before_val is None or after_val is None:
        return False

    return before_val in (True, "true") and after_val in (False, "false")


def _is_force_destroy_enabled(before: Any, after: Any) -> bool:
    """Check if force_destroy is being enabled (false -> true)."""
    before_val = before.get("force_destroy") if isinstance(before, dict) else None
    after_val = after.get("force_destroy") if isinstance(after, dict) else None

    if before_val is None or after_val is None:
        return False

    return before_val in (False, "false") and after_val in (True, "true")


def detect_state_destructive_updates(plan_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Detect state-destructive updates in Terraform plan.

    Looks for:
    - force_destroy: false -> true (S3 bucket can now be destroyed with contents)
    - prevent_destroy: true -> false (lifecycle protection removed)
    - deletion_protection: enabled -> disabled (RDS/DB protection removed)

    Args:
        plan_data: Raw Terraform plan JSON dictionary

    Returns:
        List of dicts with 'resource_address', 'resource_type' keys
    """
    result: List[Dict[str, Any]] = []
    resource_changes = plan_data.get("resource_changes", [])

    for rc in resource_changes:
        if not isinstance(rc, dict):
            continue
        address = rc.get("address", "")
        change = rc.get("change", {})
        if not change:
            continue

        actions = change.get("actions", [])
        if "update" not in actions and "create" not in actions:
            continue

        before = change.get("before") or {}
        after = change.get("after") or {}

        if not isinstance(before, dict):
            before = {}
        if not isinstance(after, dict):
            after = {}

        if (
            _is_deletion_protection_disabled(before, after)
            or _is_prevent_destroy_disabled(before, after)
            or _is_force_destroy_enabled(before, after)
        ):
            resource_type = _parse_resource_type(address)
            result.append({"resource_address": address, "resource_type": resource_type})
            logger.debug(f"State-destructive update detected: {address}")

    if result:
        logger.info(f"Detected {len(result)} state-destructive update(s)")
    return result
