from ...schema.models import RenderedPlan, ChangeReport
from .checkpoints import snapshot_checkpoint, rollback_to_checkpoint
from ..util.shell import run
from . import nft as apply_nft
from ..audit_log import log_checkpoint_creation, log_command_execution, log_plan_application
import tempfile
import os


def apply_rendered_plan(rendered_plan: dict, checkpoint_label: str | None = None) -> dict:
    try:
        plan = RenderedPlan(**rendered_plan)
    except Exception as e:
        return {
            "applied": False,
            "dry_run": False,
            "commands_preview": rendered_plan,
            "errors": [f"Invalid RenderedPlan: {e}"],
            "checkpoint_id": None,
            "notes": ["Validation failed"]
        }
    
    errors = []
    notes = []
    checkpoint_id = None
    
    # Create checkpoint before applying changes
    try:
        checkpoint_result = snapshot_checkpoint(checkpoint_label)
        checkpoint_id = checkpoint_result.get("checkpoint_id")
        notes.append(f"Created checkpoint: {checkpoint_id}")
        
        # Log checkpoint creation
        log_checkpoint_creation(checkpoint_id, checkpoint_label)
    except Exception as e:
        errors.append(f"Failed to create checkpoint: {e}")
        return {
            "applied": False,
            "dry_run": False,
            "commands_preview": rendered_plan,
            "errors": errors,
            "checkpoint_id": None,
            "notes": notes
        }
    
    applied_steps = []
    
    try:
        # 1. Apply sysctl commands
        if plan.sysctl_cmds:
            notes.append(f"Applying {len(plan.sysctl_cmds)} sysctl commands")
            for cmd in plan.sysctl_cmds:
                # Parse sysctl command: "sysctl -w key=value"
                parts = cmd.split()
                if len(parts) >= 3 and parts[0] == "sysctl" and parts[1] == "-w":
                    r = run(["sysctl", "-w", parts[2]], timeout=10)
                    
                    # Log command execution
                    log_command_execution(
                        ["sysctl", "-w", parts[2]],
                        r.get("ok"),
                        r.get("stdout", ""),
                        r.get("stderr", ""),
                        checkpoint_id
                    )
                    
                    if not r.get("ok"):
                        errors.append(f"sysctl failed: {cmd} - {r.get('stderr','')}\n{r.get('stdout','')}")
                        raise RuntimeError("sysctl command failed")
                    applied_steps.append(("sysctl", cmd))
                    notes.append(f"✓ {cmd}")
                else:
                    errors.append(f"Invalid sysctl command format: {cmd}")
                    raise ValueError(f"Invalid sysctl command format: {cmd}")
        
        # 2. Apply tc script
        if plan.tc_script and plan.tc_script.strip():
            notes.append("Applying tc script")
            # Execute lines deterministically via allowlisted runner
            for raw in plan.tc_script.splitlines():
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split()
                r = run(parts, timeout=10)
                
                # Log command execution
                log_command_execution(
                    parts,
                    r.get("ok"),
                    r.get("stdout", ""),
                    r.get("stderr", ""),
                    checkpoint_id
                )
                
                if not r.get("ok"):
                    errors.append(f"tc failed: {line} - {r.get('stderr','')}")
                    raise RuntimeError("tc command failed")
                notes.append(f"✓ {line}")
            applied_steps.append(("tc", "script"))
            notes.append("✓ tc script applied successfully")
        
        # 3. Apply nftables script
        if plan.nft_script and plan.nft_script.strip():
            notes.append("Applying nftables script")
            r = apply_nft.apply_nft_ruleset(plan.nft_script)
            
            # Log nftables execution
            log_command_execution(
                ["nft", "-f", "<script>"],
                r.get("ok"),
                r.get("stdout", ""),
                r.get("stderr", ""),
                checkpoint_id
            )
            
            if not r.get("ok"):
                errors.append(f"nftables script failed: {r.get('stderr','')}")
                raise RuntimeError("nft apply failed")
            applied_steps.append(("nft", "script"))
            notes.append("✓ nftables script applied successfully")
        
        # Success
        notes.append(f"All changes applied successfully ({len(applied_steps)} operations)")
        
        change_report = {
            "applied": True,
            "dry_run": False,
            "commands_preview": rendered_plan,
            "errors": [],
            "checkpoint_id": checkpoint_id,
            "notes": notes
        }
        
        # Log the complete plan application
        log_plan_application(rendered_plan, change_report, checkpoint_id)
        
        return change_report
    
    except Exception as e:
        # Rollback on any failure
        notes.append(f"ERROR: {e}")
        notes.append(f"Rolling back to checkpoint {checkpoint_id}")
        
        try:
            rollback_result = rollback_to_checkpoint(checkpoint_id)
            if rollback_result.get("ok"):
                notes.append("✓ Rollback successful")
            else:
                notes.append(f" Rollback failed: {rollback_result.get('notes')}")
                errors.append("Rollback failed - system may be in inconsistent state")
        except Exception as rollback_error:
            notes.append(f" Rollback exception: {rollback_error}")
            errors.append(f"Critical: Rollback failed with exception: {rollback_error}")
        
        change_report = {
            "applied": False,
            "dry_run": False,
            "commands_preview": rendered_plan,
            "errors": errors,
            "checkpoint_id": checkpoint_id,
            "notes": notes
        }
        
        # Log the failed plan application
        log_plan_application(rendered_plan, change_report, checkpoint_id)
        
        return change_report