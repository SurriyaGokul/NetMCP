from tools.planner import render_change_plan
from tools.validator import validate_change_plan
from tools.apply.apply import apply_rendered_plan
from tools.apply.checkpoints import snapshot_checkpoint, rollback_to_checkpoint

def register_tools(server):
    server.add_tool(
        name="render_change_plan",
        func= render_change_plan,
        description="Render a ParameterPlan into concrete command lists/scripts. No side effects."
    )
    server.add_tool(
        name="validate_change_plan",
        func= validate_change_plan,
        description="Schema + policy validation for a ParameterPlan."
    )
    server.add_tool(
        name="apply_rendered_plan",
        func= apply_rendered_plan,
        description="Apply a previously rendered plan atomically, with rollback on failure."
    )
    server.add_tool(
        name="snapshot_checkpoint",
        func= snapshot_checkpoint,
        description="Save the current network state for rollback."
    )
    server.add_tool(
        name="rollback_to_checkpoint",
        func= rollback_to_checkpoint,
        description="Restore a previously saved network state."
    )

