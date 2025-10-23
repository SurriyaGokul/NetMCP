# server/registry.py
from server.tools import planner, validator
from server.tools.apply import checkpoints, apply

def register_tools(server):
    server.add_tool(
        name="render_change_plan",
        func=planner.render_change_plan,
        description="Render a ParameterPlan into concrete command lists/scripts. No side effects."
    )
    server.add_tool(
        name="validate_change_plan",
        func=validator.validate_change_plan,
        description="Schema + policy validation for a ParameterPlan."
    )
    server.add_tool(
        name="apply_rendered_plan",
        func=apply.apply_rendered_plan,
        description="Apply a previously rendered plan atomically, with rollback on failure."
    )
    server.add_tool(
        name="snapshot_checkpoint",
        func=checkpoints.snapshot_checkpoint,
        description="Save the current network state for rollback."
    )
    server.add_tool(
        name="rollback_to_checkpoint",
        func=checkpoints.rollback_to_checkpoint,
        description="Restore a previously saved network state."
    )
