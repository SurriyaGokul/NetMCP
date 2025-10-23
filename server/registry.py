def register_tools(mcp):
    """
    Register all tools with the FastMCP server using decorators.
    """
    from tools.planner import render_change_plan
    from tools.validator import validate_change_plan
    from tools.apply.apply import apply_rendered_plan
    from tools.apply.checkpoints import snapshot_checkpoint, rollback_to_checkpoint

    # Register render_change_plan tool
    mcp.tool(render_change_plan)
    
    # Register validate_change_plan tool
    mcp.tool(validate_change_plan)
    
    # Register apply_rendered_plan tool
    mcp.tool(apply_rendered_plan)
    
    # Register snapshot_checkpoint tool
    mcp.tool(snapshot_checkpoint)
    
    # Register rollback_to_checkpoint tool
    mcp.tool(rollback_to_checkpoint)

