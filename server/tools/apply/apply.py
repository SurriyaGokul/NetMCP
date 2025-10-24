def apply_rendered_plan(rendered_plan: dict, checkpoint_label: str | None = None, policy_registry=None) -> dict:
    """
    Apply a rendered plan atomically with rollback capability.
    
    INPUT:  RenderedPlan dict
    OUTPUT: ChangeReport dict:
      { "applied": bool, "dry_run": bool, "commands_preview": {...}, "errors": [], 
        "checkpoint_id": str, "notes": [] }
    
    Args:
        rendered_plan: The rendered plan containing commands to execute
        checkpoint_label: Optional label for the checkpoint
        policy_registry: PolicyRegistry instance for accessing apply_tool mappings and defaults
    """
    from schema.models import RenderedPlan, ChangeReport
    from tools.apply.checkpoints import snapshot_checkpoint, rollback_to_checkpoint
    from tools.util.shell import run, run_script
    import tempfile
    import os

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
    
    try:
        checkpoint_result = snapshot_checkpoint(checkpoint_label, policy_registry)
        checkpoint_id = checkpoint_result.get("checkpoint_id")
        notes.append(f"Created checkpoint: {checkpoint_id}")
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
                try:
                    # Parse sysctl command: "sysctl -w key=value"
                    parts = cmd.split()
                    if len(parts) >= 3 and parts[0] == "sysctl" and parts[1] == "-w":
                        output = run(["/usr/sbin/sysctl", "-w", parts[2]], timeout=10)
                        applied_steps.append(("sysctl", cmd))
                        notes.append(f"✓ {cmd}")
                    else:
                        raise ValueError(f"Invalid sysctl command format: {cmd}")
                except Exception as e:
                    errors.append(f"sysctl failed: {cmd} - {e}")
                    raise
        
        # 2. Apply tc script
        if plan.tc_script and plan.tc_script.strip():
            notes.append("Applying tc script")
            try:
                # Write script to temporary file for better error reporting
                with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
                    f.write("#!/bin/bash\n")
                    f.write("set -e\n")  # Exit on error
                    f.write(plan.tc_script)
                    script_path = f.name
                
                try:
                    os.chmod(script_path, 0o755)
                    output = run_script(plan.tc_script, ["/bin/bash", "-c"], timeout=30)
                    applied_steps.append(("tc", "script"))
                    notes.append("✓ tc script applied successfully")
                finally:
                    os.unlink(script_path)
            except Exception as e:
                errors.append(f"tc script failed: {e}")
                raise
        
        # 3. Apply nftables script
        if plan.nft_script and plan.nft_script.strip():
            notes.append("Applying nftables script")
            try:
                with tempfile.NamedTemporaryFile(mode='w', suffix='.nft', delete=False) as f:
                    f.write(plan.nft_script)
                    nft_path = f.name
                
                try:
                    os.chmod(nft_path, 0o644)
                    output = run(["/usr/sbin/nft", "-f", nft_path], timeout=30)
                    applied_steps.append(("nft", "script"))
                    notes.append("✓ nftables script applied successfully")
                finally:
                    os.unlink(nft_path)
            except Exception as e:
                errors.append(f"nftables script failed: {e}")
                raise
        
        # 4. Apply ethtool commands
        if plan.ethtool_cmds:
            notes.append(f"Applying {len(plan.ethtool_cmds)} ethtool commands")
            for cmd in plan.ethtool_cmds:
                try:
                    # Parse ethtool command: "ethtool -K iface param state"
                    parts = cmd.split()
                    if len(parts) >= 5 and parts[0] == "ethtool":
                        output = run(["/usr/sbin/ethtool"] + parts[1:], timeout=10)
                        applied_steps.append(("ethtool", cmd))
                        notes.append(f"✓ {cmd}")
                    else:
                        raise ValueError(f"Invalid ethtool command format: {cmd}")
                except Exception as e:
                    errors.append(f"ethtool failed: {cmd} - {e}")
                    raise
        
        # 5. Apply ip link commands
        if plan.ip_link_cmds:
            notes.append(f"Applying {len(plan.ip_link_cmds)} ip link commands")
            for cmd in plan.ip_link_cmds:
                try:
                    # Parse ip link command: "ip link set dev iface mtu value"
                    parts = cmd.split()
                    if len(parts) >= 6 and parts[0] == "ip" and parts[1] == "link":
                        output = run(["/usr/sbin/ip"] + parts[1:], timeout=10)
                        applied_steps.append(("ip", cmd))
                        notes.append(f"✓ {cmd}")
                    else:
                        raise ValueError(f"Invalid ip command format: {cmd}")
                except Exception as e:
                    errors.append(f"ip link failed: {cmd} - {e}")
                    raise
        
        # Success
        notes.append(f"All changes applied successfully ({len(applied_steps)} operations)")
        return {
            "applied": True,
            "dry_run": False,
            "commands_preview": rendered_plan,
            "errors": [],
            "checkpoint_id": checkpoint_id,
            "notes": notes
        }
    
    except Exception as e:
        # Rollback on any failure
        notes.append(f"ERROR: {e}")
        notes.append(f"Rolling back to checkpoint {checkpoint_id}")
        
        try:
            rollback_result = rollback_to_checkpoint(checkpoint_id, policy_registry)
            if rollback_result.get("ok"):
                notes.append("✓ Rollback successful")
            else:
                notes.append(f" Rollback failed: {rollback_result.get('notes')}")
                errors.append("Rollback failed - system may be in inconsistent state")
        except Exception as rollback_error:
            notes.append(f" Rollback exception: {rollback_error}")
            errors.append(f"Critical: Rollback failed with exception: {rollback_error}")
        
        return {
            "applied": False,
            "dry_run": False,
            "commands_preview": rendered_plan,
            "errors": errors,
            "checkpoint_id": checkpoint_id,
            "notes": notes
        }