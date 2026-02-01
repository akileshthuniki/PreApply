"""Translate Terraform's raw data into clean, provider-agnostic internal model."""

import re
from typing import Dict, Any, List
from .models import NormalizedResource, NormalizedPlan, ResourceAction
from ..utils.errors import NormalizationError
from ..utils.logging import get_logger

logger = get_logger("ingest.plan_normalizer")


def _parse_resource_address(address: str) -> tuple[str, str, str]:
    """Parse Terraform resource address into (resource_id, module_path, resource_type)."""
    address = address.strip()
    parts = address.split('.')
    
    resource_type_idx = None
    for i, part in enumerate(parts):
        if '_' in part and part not in ['module']:
            resource_type_idx = i
            break
    
    if resource_type_idx is None:
        raise NormalizationError(f"Cannot find resource type in address: {address}")
    
    resource_type = parts[resource_type_idx]
    resource_name_parts = parts[resource_type_idx + 1:] if resource_type_idx + 1 < len(parts) else []
    resource_name = '.'.join(resource_name_parts) if resource_name_parts else resource_type
    
    resource_id = f"{resource_type}.{resource_name}" if resource_name != resource_type else resource_type
    
    if resource_type_idx > 0:
        module_parts = []
        i = 0
        while i < resource_type_idx:
            if parts[i] == 'module' and i + 1 < resource_type_idx:
                module_parts.append(parts[i + 1])
                i += 2
            else:
                i += 1
        module_path = '.'.join(module_parts) if module_parts else None
    else:
        module_path = None
    
    return (resource_id, module_path, resource_type)


def _normalize_action(actions: List[str]) -> ResourceAction:
    """
    Normalize Terraform action list to single ResourceAction.
    
    Terraform actions can be: ["create"], ["update"], ["delete"], ["read"], 
    ["create", "update"], ["update", "delete"], etc.
    
    Args:
        actions: List of Terraform action strings
        
    Returns:
        Normalized ResourceAction
    """
    if not actions:
        return ResourceAction.NO_OP
    
    # Normalize to uppercase
    normalized = [a.upper() for a in actions]
    
    # Priority: DELETE > UPDATE > CREATE > READ
    if "delete" in normalized or "DELETE" in normalized:
        return ResourceAction.DELETE
    elif "update" in normalized or "UPDATE" in normalized:
        return ResourceAction.UPDATE
    elif "create" in normalized or "CREATE" in normalized:
        return ResourceAction.CREATE
    elif "read" in normalized or "READ" in normalized:
        return ResourceAction.READ
    else:
        return ResourceAction.NO_OP


def _extract_dependencies_from_expressions(expressions: Dict[str, Any]) -> List[str]:
    """
    Extract resource references from Terraform configuration expressions.
    
    Terraform plan JSON stores dependencies in configuration.root_module.resources[].expressions
    where each expression can have a 'references' array.
    
    Args:
        expressions: Dictionary of expression objects from configuration
        
    Returns:
        List of resource addresses this resource depends on
    """
    deps = set()
    
    def extract_from_expression(expr: Any) -> None:
        """Recursively extract references from expression structure."""
        if isinstance(expr, dict):
            # Check if this is a reference expression
            if 'references' in expr:
                refs = expr['references']
                for ref in refs:
                    if isinstance(ref, str):
                        # Extract resource address from reference
                        # Examples:
                        #   "aws_lb.shared.arn" -> "aws_lb.shared"
                        #   "aws_lb.shared" -> "aws_lb.shared"
                        #   "module.vpc.aws_vpc.main.id" -> "module.vpc.aws_vpc.main"
                        parts = ref.split('.')
                        if len(parts) >= 2:
                            # Check if last part is an attribute
                            last_part = parts[-1].lower()
                            common_attrs = ['id', 'arn', 'name', 'key', 'value', 'output', 'address', 'port', 'protocol']
                            if last_part in common_attrs and len(parts) > 2:
                                # Last part is likely an attribute, resource is everything before
                                resource_addr = '.'.join(parts[:-1])
                            else:
                                # Could be resource name or attribute, try to find resource boundary
                                # Look for resource type pattern (has underscore like aws_vpc)
                                resource_type_idx = None
                                for i, part in enumerate(parts):
                                    if '_' in part and part not in ['module']:
                                        resource_type_idx = i
                                        break
                                
                                if resource_type_idx is not None:
                                    # Resource address is from type to end (or before attribute)
                                    if resource_type_idx + 1 < len(parts):
                                        # Check if last part is attribute
                                        if parts[-1].lower() in common_attrs:
                                            resource_addr = '.'.join(parts[resource_type_idx:-1])
                                        else:
                                            resource_addr = '.'.join(parts[resource_type_idx:])
                                    else:
                                        resource_addr = parts[resource_type_idx]
                                else:
                                    # Fallback: use all parts
                                    resource_addr = '.'.join(parts)
                            
                            # Filter out non-resource references
                            # Skip variables, data sources, and provider configs
                            skip_patterns = ['var.', 'data.', 'aws_region', 'aws_account', 'local.', 'path.']
                            is_resource = (
                                ('_' in resource_addr or resource_addr.startswith('module.')) and
                                not any(resource_addr.startswith(pattern) for pattern in skip_patterns)
                            )
                            if is_resource:
                                deps.add(resource_addr)
            
            # Recursively check nested structures
            for value in expr.values():
                extract_from_expression(value)
        elif isinstance(expr, list):
            for item in expr:
                extract_from_expression(item)
    
    extract_from_expression(expressions)
    return list(deps)


def _extract_dependencies(
    resource_change: Dict[str, Any],
    configuration_resources: Dict[str, Dict[str, Any]] = None
) -> List[str]:
    """
    Extract dependency list from Terraform resource change.
    
    Dependencies come from multiple sources:
    1. Explicit depends_on field in resource_changes
    2. References in configuration.root_module.resources[].expressions
    3. Implicit references in change.before/after (fallback)
    
    Args:
        resource_change: Terraform resource_change object
        configuration_resources: Optional dict mapping resource addresses to their configuration
        
    Returns:
        List of resource addresses this resource depends on
    """
    address = resource_change.get("address", "")
    deps = set()
    
    # 1. Explicit depends_on
    depends_on = resource_change.get("depends_on", [])
    if depends_on:
        deps.update(depends_on)
    
    # 2. Extract from configuration expressions (most reliable)
    if configuration_resources and address in configuration_resources:
        config_resource = configuration_resources[address]
        expressions = config_resource.get("expressions", {})
        if expressions:
            expr_deps = _extract_dependencies_from_expressions(expressions)
            deps.update(expr_deps)
    
    # 3. Fallback: Extract from change.before and change.after (for string interpolation)
    change = resource_change.get("change", {})
    before = change.get("before", {})
    after = change.get("after", {})
    
    def extract_string_refs(value: Any) -> List[str]:
        """Extract resource references from string values (fallback)."""
        refs = []
        if isinstance(value, str):
            # Look for patterns like ${aws_vpc.main.id}
            matches = re.findall(r'\$\{([^}]+)\}', value)
            for match in matches:
                parts = match.split('.')
                if len(parts) >= 2:
                    last_part = parts[-1].lower()
                    if last_part in ['id', 'arn', 'name', 'key', 'value', 'output']:
                        resource_addr = '.'.join(parts[:-1])
                    else:
                        resource_addr = '.'.join(parts)
                    refs.append(resource_addr)
                elif len(parts) == 1:
                    refs.append(parts[0])
        elif isinstance(value, dict):
            for v in value.values():
                refs.extend(extract_string_refs(v))
        elif isinstance(value, list):
            for item in value:
                refs.extend(extract_string_refs(item))
        return refs
    
    string_deps = extract_string_refs(before) + extract_string_refs(after)
    deps.update(string_deps)
    
    # Remove self-reference and return
    deps.discard(address)
    return list(deps)


def _build_configuration_resource_map(plan_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Build a map of resource addresses to their configuration expressions.
    
    This reads from configuration.root_module.resources to get actual
    resource references that Terraform uses for dependency resolution.
    
    Args:
        plan_data: Raw Terraform plan JSON dictionary
        
    Returns:
        Dictionary mapping resource addresses to their configuration
    """
    config_map = {}
    configuration = plan_data.get("configuration", {})
    root_module = configuration.get("root_module", {})
    
    # Process root module resources
    for resource in root_module.get("resources", []):
        address = resource.get("address", "")
        if address:
            config_map[address] = resource
    
    # Process child modules recursively
    def process_module(module: Dict[str, Any], prefix: str = "") -> None:
        for child_module in module.get("child_modules", []):
            module_address = child_module.get("address", "")
            for resource in child_module.get("resources", []):
                resource_address = resource.get("address", "")
                if resource_address:
                    # Full address includes module path
                    full_address = resource_address if not module_address else f"{module_address}.{resource_address}"
                    config_map[full_address] = resource
            # Recursively process nested modules
            process_module(child_module, module_address)
    
    process_module(root_module)
    
    return config_map


def normalize_plan(plan_data: Dict[str, Any]) -> NormalizedPlan:
    """
    Normalize Terraform plan JSON into clean, provider-agnostic format.
    
    This function:
    - Converts Terraform-specific structures into consistent field names
    - Normalizes action types
    - Removes fields irrelevant to risk analysis
    - Produces predictable internal format
    - Extracts dependencies from configuration expressions
    
    Args:
        plan_data: Raw Terraform plan JSON dictionary
        
    Returns:
        NormalizedPlan with clean resource models
        
    Raises:
        NormalizationError: If normalization fails
    """
    try:
        resource_changes = plan_data.get("resource_changes", [])
        
        # Build configuration resource map for dependency extraction
        config_resource_map = _build_configuration_resource_map(plan_data)
        
        normalized_resources = []
        
        for resource_change in resource_changes:
            try:
                address = resource_change.get("address", "")
                if not address:
                    logger.warning("Skipping resource change with no address")
                    continue
                
                # Parse address
                resource_id, module_path, resource_type = _parse_resource_address(address)
                
                # Normalize action
                change = resource_change.get("change", {})
                actions = change.get("actions", [])
                action = _normalize_action(actions)
                
                # Extract dependencies (now uses configuration expressions)
                depends_on = _extract_dependencies(resource_change, config_resource_map)
                
                # Create normalized resource
                normalized = NormalizedResource(
                    id=resource_id,
                    module=module_path,
                    type=resource_type,
                    action=action,
                    depends_on=depends_on,
                    metadata={}  # Can be extended later if needed
                )
                
                normalized_resources.append(normalized)
                
            except Exception as e:
                logger.warning(f"Failed to normalize resource {resource_change.get('address', 'unknown')}: {e}")
                continue
        
        logger.info(f"Normalized {len(normalized_resources)} resources from plan")
        return NormalizedPlan(resources=normalized_resources)
        
    except Exception as e:
        raise NormalizationError(f"Failed to normalize plan: {e}")

