def register_tools(mcp):
    """
    Register all tools with the FastMCP server using decorators.
    Tools receive server.state via dependency injection to access PolicyRegistry.
    """
    from tools.planner import render_change_plan
    from tools.validator import validate_change_plan
    from tools.apply.apply import apply_rendered_plan
    from tools.apply.checkpoints import snapshot_checkpoint, rollback_to_checkpoint

    # Create wrapper functions that inject server state (policy registry)
    
    @mcp.tool
    def render_change_plan_tool(plan: dict) -> dict:
        """
        Render a ParameterPlan into concrete command lists/scripts. No side effects.
        """
        policy = mcp.state.get("policy")
        return render_change_plan(plan, policy)
    
    @mcp.tool
    def validate_change_plan_tool(parameter_plan: dict) -> dict:
        """
        Schema + policy validation for a ParameterPlan.
        """
        policy = mcp.state.get("policy")
        return validate_change_plan(parameter_plan, policy)
    
    @mcp.tool
    def apply_rendered_plan_tool(rendered_plan: dict, checkpoint_label: str = None) -> dict:
        """
        Apply a previously rendered plan atomically, with rollback on failure.
        """
        policy = mcp.state.get("policy")
        return apply_rendered_plan(rendered_plan, checkpoint_label, policy)
    
    @mcp.tool
    def snapshot_checkpoint_tool(label: str = None) -> dict:
        """
        Save the current network state for rollback.
        """
        policy = mcp.state.get("policy")
        return snapshot_checkpoint(label, policy)
    
    @mcp.tool
    def rollback_to_checkpoint_tool(checkpoint_id: str) -> dict:
        """
        Restore a previously saved network state.
        """
        policy = mcp.state.get("policy")
        return rollback_to_checkpoint(checkpoint_id, policy)

