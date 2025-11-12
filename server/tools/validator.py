import yaml
from pathlib import Path
from typing import Dict, Any
from ..schema.models import ParameterPlan
from .audit_log import log_plan_validation

# Cache for validation limits (loaded once)
_validation_limits_cache: Dict[str, Any] = None

def load_validation_limits() -> Dict[str, Any]:
    """Load validation limits from YAML file (cached)."""
    global _validation_limits_cache
    
    if _validation_limits_cache is not None:
        return _validation_limits_cache
    
    limits_file = Path(__file__).parent.parent.parent / "policy" / "validation_limits.yaml"
    
    try:
        with open(limits_file, 'r') as f:
            data = yaml.safe_load(f)
            _validation_limits_cache = data.get('validation_limits', {})
            return _validation_limits_cache
    except Exception as e:
        # Fallback to hardcoded defaults if file cannot be loaded
        print(f"Warning: Could not load validation_limits.yaml: {e}")
        _validation_limits_cache = {
            'bandwidth': {'max_mbps': 100000, 'min_mbps': 1},
            'dscp': {'valid_values': ["EF", "CS6", "CS5", "CS4", "AF41", "AF42", "AF43"]},
            'plan_structure': {
                'valid_top_keys': ["iface", "profile", "changes", "validation", "rationale"],
                'valid_change_keys': ["qdisc", "shaper", "netem", "htb_classes", "sysctl", "dscp", 
                                      "connection_limits", "rate_limits", "connection_tracking", "nat_rules"],
                'valid_qdisc_keys': ["type", "params"]
            }
        }
        return _validation_limits_cache

def validate_change_plan(parameter_plan: dict) -> dict:
    """
    INPUT:  ParameterPlan dict
    OUTPUT: {"ok": bool, "errors": [str], "plan": dict}
    
    Args:
        parameter_plan: The parameter plan to validate
    
    Validates:
        - DSCP values are within valid range
        - Bandwidth values are within limits
        - No unknown keys are present in the plan
        - All required fields are present
    """    
    
    # Load validation limits from YAML
    limits = load_validation_limits()
    
    if not isinstance(parameter_plan, dict):
        return {"ok": False, "errors": ["parameter_plan must be of type dict"], "plan": None}
    
    errors = []
    
    # Get valid keys from limits
    structure = limits.get('plan_structure', {})
    valid_top_keys = set(structure.get('valid_top_keys', 
        ["iface", "profile", "changes", "validation", "rationale"]))
    
    unknown_keys = set(parameter_plan.keys()) - valid_top_keys
    if unknown_keys:
        errors.append(f"Unknown top-level keys: {', '.join(sorted(unknown_keys))}")

    try:
        validated_plan = ParameterPlan(**parameter_plan)
    except Exception as e:
        errors.append(f"Schema validation failed: {str(e)}")
        return {"ok": False, "errors": errors, "plan": None}
    
    # Validate profile name against profiles.yaml
    # Note: "balanced" is a special validation-only profile, not in profiles.yaml
    VALID_PROFILES = ["gaming", "streaming", "video_calls", "bulk_transfer", "server"]
    if validated_plan.profile not in VALID_PROFILES:
        errors.append(
            f"Invalid profile '{validated_plan.profile}'. Must be one of: {', '.join(VALID_PROFILES)}"
        )
    
    # Additional validation: DSCP values
    if validated_plan.changes.dscp:
        dscp_config = limits.get('dscp', {})
        valid_dscp = set(dscp_config.get('valid_values', 
            ["EF", "CS6", "CS5", "CS4", "AF41", "AF42", "AF43"]))
        
        for rule in validated_plan.changes.dscp:
            if rule.dscp not in valid_dscp:
                errors.append(
                    f"Invalid DSCP value: {rule.dscp}. Must be one of {sorted(valid_dscp)}"
                )
    
    # Additional validation: Bandwidth limits
    if validated_plan.changes.shaper:
        shaper = validated_plan.changes.shaper
        bandwidth_config = limits.get('bandwidth', {})
        max_mbps = bandwidth_config.get('max_mbps', 100000)
        min_mbps = bandwidth_config.get('min_mbps', 1)
        
        # Check for over-bandwidth (exceeds maximum)
        if shaper.egress_mbit and shaper.egress_mbit > max_mbps:
            errors.append(
                f"egress_mbit {shaper.egress_mbit} exceeds maximum of {max_mbps}"
            )
        
        if shaper.ingress_mbit and shaper.ingress_mbit > max_mbps:
            errors.append(
                f"ingress_mbit {shaper.ingress_mbit} exceeds maximum of {max_mbps}"
            )
        
        if shaper.ceil_mbit and shaper.ceil_mbit > max_mbps:
            errors.append(
                f"ceil_mbit {shaper.ceil_mbit} exceeds maximum of {max_mbps}"
            )
        
        # Check for under-bandwidth (below minimum)
        if shaper.egress_mbit and shaper.egress_mbit < min_mbps:
            errors.append(
                f"egress_mbit {shaper.egress_mbit} is below minimum of {min_mbps}"
            )
        
        if shaper.ingress_mbit and shaper.ingress_mbit < min_mbps:
            errors.append(
                f"ingress_mbit {shaper.ingress_mbit} is below minimum of {min_mbps}"
            )
        
        # Check ceil is greater than or equal to rate
        if shaper.egress_mbit and shaper.ceil_mbit:
            if shaper.ceil_mbit < shaper.egress_mbit:
                errors.append(
                    f"ceil_mbit {shaper.ceil_mbit} must be >= egress_mbit {shaper.egress_mbit}"
                )
    
    # Check for unknown keys in changes
    if "changes" in parameter_plan:
        valid_change_keys = set(structure.get('valid_change_keys',
            ["qdisc", "shaper", "netem", "htb_classes", "sysctl", "dscp", 
             "connection_limits", "rate_limits", "connection_tracking", "nat_rules"]))
        unknown_change_keys = set(parameter_plan["changes"].keys()) - valid_change_keys
        if unknown_change_keys:
            errors.append(f"Unknown keys in changes: {', '.join(sorted(unknown_change_keys))}")
    
    # Check for unknown keys in nested objects
    if validated_plan.changes.qdisc and "qdisc" in parameter_plan.get("changes", {}):
        valid_qdisc_keys = set(structure.get('valid_qdisc_keys', ["type", "params"]))
        unknown_qdisc_keys = set(parameter_plan["changes"]["qdisc"].keys()) - valid_qdisc_keys
        if unknown_qdisc_keys:
            errors.append(f"Unknown keys in qdisc: {', '.join(sorted(unknown_qdisc_keys))}")
    
    if errors:
        result = {"ok": False, "errors": errors, "plan": None}
        log_plan_validation(parameter_plan, result)
        return result
    
    result = {"ok": True, "errors": [], "plan": validated_plan.model_dump()}
    log_plan_validation(parameter_plan, result)
    return result
