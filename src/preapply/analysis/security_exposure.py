"""Detect security exposures in Terraform plan (public CIDR, S3 public access, port sensitivity)."""

from typing import Dict, Any, List, Optional
from ..contracts.risk_attributes import SecurityExposure
from ..utils.logging import get_logger

logger = get_logger("analysis.security_exposure")

GLOBAL_CIDRS = ("0.0.0.0/0", "::/0")
SENSITIVE_PORTS = (22, 3389, 1433, 3306, 5432, 5439, 27017)  # SSH, RDP, MSSQL, MySQL, PostgreSQL, Redshift, MongoDB


def _get_exposure_port(from_port: Any, to_port: Any) -> Optional[int]:
    """
    Get port for exposure penalty: single port or sensitive from_port in range.
    If from_port == to_port use that port; if range and from_port is sensitive use from_port; else None.
    """
    try:
        low = int(from_port) if from_port is not None else None
        high = int(to_port) if to_port is not None else None
        if low is None:
            return None
        if high is None:
            high = low
        if low == high:
            return low
        if low in SENSITIVE_PORTS:
            return low
        return None
    except (TypeError, ValueError):
        return None


def _has_global_cidr(cidr_blocks: List[str], ipv6_blocks: List[str] = None) -> bool:
    """Check if any CIDR is globally open."""
    ipv6_blocks = ipv6_blocks or []
    for cidr in (cidr_blocks or []) + ipv6_blocks:
        cidr = (cidr or "").strip()
        if cidr in GLOBAL_CIDRS:
            return True
    return False


def _is_port_sensitive(from_port: Any, to_port: Any) -> bool:
    """Check if port range includes any sensitive port."""
    try:
        low = int(from_port) if from_port is not None else 0
        high = int(to_port) if to_port is not None else 65535
        for p in SENSITIVE_PORTS:
            if low <= p <= high:
                return True
    except (TypeError, ValueError):
        pass
    return False


def _check_security_group_rules(address: str, resource_type: str, change: Dict[str, Any]) -> List[SecurityExposure]:
    """Check aws_security_group ingress/egress for public exposure."""
    exposures = []
    # Prefer 'after' (create/update); use 'before' for delete
    side = change.get("after") or change.get("before") or {}
    if not side:
        return exposures

    for rule_type in ("ingress", "egress"):
        rules = side.get(rule_type, [])
        if not isinstance(rules, list):
            continue
        for rule in rules:
            if not isinstance(rule, dict):
                continue
            cidr_blocks = rule.get("cidr_blocks") or []
            ipv6_blocks = rule.get("ipv6_cidr_blocks") or []
            if not _has_global_cidr(cidr_blocks, ipv6_blocks):
                continue
            from_port = rule.get("from_port")
            to_port = rule.get("to_port")
            port_sensitive = _is_port_sensitive(from_port, to_port)
            port_val = _get_exposure_port(from_port, to_port)
            port_desc = f" (Port {port_val} exposed)" if port_val and port_sensitive else (" (sensitive port exposed)" if port_sensitive else "")
            details = f"{rule_type} open to 0.0.0.0/0 or ::/0{port_desc}"
            exposures.append(SecurityExposure(
                resource_id=address,
                resource_type=resource_type,
                exposure_type="public_cidr",
                details=details.strip(),
                port_sensitive=port_sensitive,
                port=port_val
            ))
    return exposures


def _check_security_group_rule_resource(address: str, resource_type: str, change: Dict[str, Any]) -> List[SecurityExposure]:
    """Check aws_vpc_security_group_ingress_rule / egress_rule resources."""
    exposures = []
    side = change.get("after") or change.get("before") or {}
    if not side:
        return exposures

    cidr_blocks = []
    ipv6_blocks = []
    cidr_ipv4 = side.get("cidr_ipv4")
    cidr_ipv6 = side.get("cidr_ipv6")
    if cidr_ipv4:
        cidr_blocks.append(cidr_ipv4)
    if cidr_ipv6:
        ipv6_blocks.append(cidr_ipv6)
    if not _has_global_cidr(cidr_blocks, ipv6_blocks):
        return exposures

    from_port = side.get("from_port")
    to_port = side.get("to_port")
    port_sensitive = _is_port_sensitive(from_port, to_port)
    port_val = _get_exposure_port(from_port, to_port)
    port_desc = f" (Port {port_val} exposed)" if port_val and port_sensitive else (" (sensitive port exposed)" if port_sensitive else "")
    details = f"Rule open to 0.0.0.0/0 or ::/0{port_desc}"
    exposures.append(SecurityExposure(
        resource_id=address,
        resource_type=resource_type,
        exposure_type="public_cidr",
        details=details.strip(),
        port_sensitive=port_sensitive,
        port=port_val
    ))
    return exposures


def _check_s3_public_access(address: str, resource_type: str, change: Dict[str, Any]) -> List[SecurityExposure]:
    """Check S3 public access block and bucket ACL."""
    exposures = []
    side = change.get("after") or change.get("before") or {}
    if not side:
        return exposures

    if resource_type == "aws_s3_bucket_public_access_block":
        block_public_acls = side.get("block_public_acls")
        block_public_policy = side.get("block_public_policy")
        if block_public_acls is False or block_public_policy is False:
            exposures.append(SecurityExposure(
                resource_id=address,
                resource_type=resource_type,
                exposure_type="s3_public",
                details="S3 public access block disabled (block_public_acls or block_public_policy false)",
                port_sensitive=False
            ))
    elif resource_type == "aws_s3_bucket":
        acl = side.get("acl")
        if acl and str(acl).lower() in ("public-read", "public-read-write"):
            exposures.append(SecurityExposure(
                resource_id=address,
                resource_type=resource_type,
                exposure_type="s3_public",
                details=f"S3 bucket ACL set to public ({acl})",
                port_sensitive=False
            ))
    return exposures


def detect_security_exposures(plan_data: Dict[str, Any]) -> List[SecurityExposure]:
    """
    Detect security exposures in Terraform plan JSON.

    Checks for:
    - Security groups / rules open to 0.0.0.0/0 or ::/0
    - Port 22 (SSH) or 3389 (RDP) exposed globally (port sensitivity)
    - S3 public access block disabled or bucket ACL public-read

    Args:
        plan_data: Raw Terraform plan JSON dictionary

    Returns:
        List of SecurityExposure objects
    """
    exposures: List[SecurityExposure] = []
    resource_changes = plan_data.get("resource_changes", [])

    for rc in resource_changes:
        if not isinstance(rc, dict):
            continue
        address = rc.get("address", "")
        change = rc.get("change", {})
        if not change:
            continue

        # Infer resource type from address (e.g. "aws_security_group.main" -> aws_security_group)
        parts = address.split(".")
        resource_type = ""
        for p in parts:
            if "_" in p and p not in ("module", "aws", "azurerm", "google"):
                resource_type = p
                break
        if not resource_type:
            continue

        if resource_type in ("aws_security_group",):
            exposures.extend(_check_security_group_rules(address, resource_type, change))
        elif resource_type in ("aws_vpc_security_group_ingress_rule", "aws_vpc_security_group_egress_rule"):
            exposures.extend(_check_security_group_rule_resource(address, resource_type, change))
        elif resource_type in ("aws_s3_bucket_public_access_block", "aws_s3_bucket"):
            exposures.extend(_check_s3_public_access(address, resource_type, change))

    if exposures:
        logger.info(f"Detected {len(exposures)} security exposure(s)")
    return exposures
