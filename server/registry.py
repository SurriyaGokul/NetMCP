def register_resources(mcp, policy_registry):
    """
    Register policy configuration cards as MCP resources.
    The LLM can read these resources to understand available network optimization options.
    """
    import json
    
    @mcp.resource("policy://config_cards/list")
    def get_policy_card_list() -> str:
        """
        Get a list of all available network optimization configuration cards.
        Each card represents a specific network parameter that can be configured.
        """
        cards = policy_registry.list()
        return json.dumps({
            "description": "Available network optimization configuration cards",
            "count": len(cards),
            "cards": cards
        }, indent=2)
    
    @mcp.resource("policy://config_cards/{card_id}")
    def get_policy_card(card_id: str) -> str:
        """
        Get detailed information about a specific configuration card.
        Includes description, use cases, parameters, impacts, and examples.
        """
        card = policy_registry.get(card_id)
        if not card:
            return json.dumps({"error": f"Configuration card '{card_id}' not found"})
        return json.dumps(card, indent=2)


def register_tools(mcp):
    """
    Register all tools with the FastMCP server using decorators.
    These tools allow the LLM to plan, validate, and apply network optimizations.
    """
    from tools.planner import render_change_plan
    from tools.validator import validate_change_plan
    from tools.apply.apply import apply_rendered_plan
    from tools.apply.checkpoints import snapshot_checkpoint, rollback_to_checkpoint
    
    @mcp.tool()
    def render_change_plan_tool(plan: dict) -> dict:
        """
        Render a ParameterPlan into concrete command lists/scripts. No side effects.
        
        Args:
            plan: A ParameterPlan dictionary containing the network changes to render
            
        Returns:
            A RenderedPlan dictionary with executable commands and scripts
        """
        return render_change_plan(plan)
    
    @mcp.tool()
    def validate_change_plan_tool(parameter_plan: dict) -> dict:
        """
        Schema + policy validation for a ParameterPlan.
        
        Args:
            parameter_plan: A ParameterPlan dictionary to validate
            
        Returns:
            A ValidationResult with ok status and any issues found
        """
        return validate_change_plan(parameter_plan)
    
    @mcp.tool()
    def apply_rendered_plan_tool(rendered_plan: dict, checkpoint_label: str = None) -> dict:
        """
        Apply a previously rendered plan atomically, with rollback on failure.
        
        Args:
            rendered_plan: A RenderedPlan dictionary with commands to execute
            checkpoint_label: Optional label for the checkpoint created before applying changes
            
        Returns:
            A ChangeReport with status, errors, and checkpoint information
        """
        return apply_rendered_plan(rendered_plan, checkpoint_label)
    
    @mcp.tool()
    def snapshot_checkpoint_tool(label: str = None) -> dict:
        """
        Save the current network state for rollback.
        
        Args:
            label: Optional label to identify this checkpoint
            
        Returns:
            Dictionary with checkpoint_id and notes
        """
        return snapshot_checkpoint(label)
    
    @mcp.tool()
    def rollback_to_checkpoint_tool(checkpoint_id: str) -> dict:
        """
        Restore a previously saved network state.
        
        Args:
            checkpoint_id: The ID of the checkpoint to restore
            
        Returns:
            Dictionary with ok status and restoration notes
        """
        return rollback_to_checkpoint(checkpoint_id)

