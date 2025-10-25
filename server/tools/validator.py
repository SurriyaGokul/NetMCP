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
    from ..schema.models import ParameterPlan
    
    if not isinstance(parameter_plan, dict):
        return {"ok": False, "errors": ["parameter_plan must be of type dict"], "plan": None}
    
    errors = []
    
    # Check for unknown top-level keys
    valid_top_keys = {"iface", "profile", "changes", "validate", "rationale"}
    unknown_keys = set(parameter_plan.keys()) - valid_top_keys
    if unknown_keys:
        errors.append(f"Unknown top-level keys: {', '.join(sorted(unknown_keys))}")
    
    # Validate using Pydantic schema
    try:
        validated_plan = ParameterPlan(**parameter_plan)
    except Exception as e:
        errors.append(f"Schema validation failed: {str(e)}")
        return {"ok": False, "errors": errors, "plan": None}
    
    # Additional validation: DSCP values
    if validated_plan.changes.dscp:
        valid_dscp = {"EF", "CS6", "CS5", "CS4", "AF41", "AF42", "AF43"}
        for rule in validated_plan.changes.dscp:
            if rule.dscp not in valid_dscp:
                errors.append(f"Invalid DSCP value: {rule.dscp}. Must be one of {valid_dscp}")
    
    # Additional validation: Bandwidth limits
    if validated_plan.changes.shaper:
        shaper = validated_plan.changes.shaper
        
        # Check for over-bandwidth (> 100Gbps)
        if shaper.egress_mbit and shaper.egress_mbit > 100000:
            errors.append(f"egress_mbit {shaper.egress_mbit} exceeds maximum of 100000")
        
        if shaper.ingress_mbit and shaper.ingress_mbit > 100000:
            errors.append(f"ingress_mbit {shaper.ingress_mbit} exceeds maximum of 100000")
        
        if shaper.ceil_mbit and shaper.ceil_mbit > 100000:
            errors.append(f"ceil_mbit {shaper.ceil_mbit} exceeds maximum of 100000")
        
        # Check ceil is greater than or equal to rate
        if shaper.egress_mbit and shaper.ceil_mbit:
            if shaper.ceil_mbit < shaper.egress_mbit:
                errors.append(f"ceil_mbit {shaper.ceil_mbit} must be >= egress_mbit {shaper.egress_mbit}")
    
    # Check for unknown keys in changes
    if "changes" in parameter_plan:
        valid_change_keys = {"qdisc", "shaper", "sysctl", "offloads", "dscp", "mtu"}
        unknown_change_keys = set(parameter_plan["changes"].keys()) - valid_change_keys
        if unknown_change_keys:
            errors.append(f"Unknown keys in changes: {', '.join(sorted(unknown_change_keys))}")
    
    # Check for unknown keys in nested objects
    if validated_plan.changes.qdisc and "qdisc" in parameter_plan.get("changes", {}):
        valid_qdisc_keys = {"type", "params"}
        unknown_qdisc_keys = set(parameter_plan["changes"]["qdisc"].keys()) - valid_qdisc_keys
        if unknown_qdisc_keys:
            errors.append(f"Unknown keys in qdisc: {', '.join(sorted(unknown_qdisc_keys))}")
    
    if validated_plan.changes.offloads and "offloads" in parameter_plan.get("changes", {}):
        valid_offload_keys = {"gro", "gso", "tso", "lro"}
        unknown_offload_keys = set(parameter_plan["changes"]["offloads"].keys()) - valid_offload_keys
        if unknown_offload_keys:
            errors.append(f"Unknown keys in offloads: {', '.join(sorted(unknown_offload_keys))}")
    
    if errors:
        return {"ok": False, "errors": errors, "plan": None}
    
    return {"ok": True, "errors": [], "plan": validated_plan.model_dump()}
