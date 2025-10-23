def apply_rendered_plan(rendered_plan: dict, checkpoint_label: str | None = None, policy_registry=None) -> dict:
    """
    INPUT:  RenderedPlan dict
    OUTPUT: ChangeReport dict:
      { "applied": false, "dry_run": true, "commands_preview": {...}, "errors": [] }
    
    Args:
        rendered_plan: The rendered plan containing commands to execute
        checkpoint_label: Optional label for the checkpoint
        policy_registry: PolicyRegistry instance for accessing apply_tool mappings and defaults
    """
    # policy_registry can be used to access config cards for apply_tool mapping
    # Example: policy_registry.get("sysctl_tcp_congestion_control")
    
    preview = {
        "sysctl_cmds": rendered_plan.get("sysctl_cmds", []),
        "tc_script": rendered_plan.get("tc_script", ""),
        "nft_script": rendered_plan.get("nft_script", ""),
        "ethtool_cmds": rendered_plan.get("ethtool_cmds", []),
        "ip_link_cmds": rendered_plan.get("ip_link_cmds", []),
    }
    return {"applied": False, "dry_run": True, "commands_preview": preview, "errors": []}
