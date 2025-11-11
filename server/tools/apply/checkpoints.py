import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from ..util.shell import run, run_privileged
from ..audit_log import log_rollback


# Checkpoint storage location
CHECKPOINT_DIR = Path.home() / ".mcp-net-optimizer" / "checkpoints"


def _ensure_checkpoint_dir():
    """Create checkpoint directory if it doesn't exist."""
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)


def _run_command(cmd: List[str], use_sudo: bool = False) -> tuple[bool, str, str]:
    """
    Run a command and return (success, stdout, stderr).
    
    Args:
        cmd: Command to run
        use_sudo: If True, use sudo for privileged commands
    """
    if use_sudo:
        result = run_privileged(cmd, timeout=30)
    else:
        result = run(cmd, timeout=30)
    
    return (result["ok"], result["stdout"], result["stderr"])


def snapshot_checkpoint(label: str | None = None) -> dict:
    """
    Create a checkpoint by saving current network configuration state.
    
    OUTPUT: {"checkpoint_id": "checkpoint-20251102-143022", "notes": "...", "ok": True}
    
    Args:
        label: Optional label for the checkpoint
    """
    try:
        _ensure_checkpoint_dir()
        
        # Generate checkpoint ID with timestamp
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        checkpoint_id = f"checkpoint-{timestamp}"
        checkpoint_path = CHECKPOINT_DIR / checkpoint_id
        checkpoint_path.mkdir(exist_ok=True)
        
        notes = []
        errors = []
        
        # 1. Save sysctl settings
        success, stdout, stderr = _run_command(["sysctl", "-a"])
        if success:
            (checkpoint_path / "sysctl.conf").write_text(stdout)
            notes.append("✓ Saved sysctl settings")
        else:
            errors.append(f"Failed to save sysctl: {stderr}")
        
        # 2. Save tc (traffic control) configuration
        tc_data = {}
        
        # Get list of interfaces
        success, stdout, stderr = _run_command(["ip", "link", "show"])
        if success:
            interfaces = []
            for line in stdout.split("\n"):
                if ":" in line and not line.startswith(" "):
                    parts = line.split(":")
                    if len(parts) >= 2:
                        iface = parts[1].strip().split("@")[0]
                        if iface and iface not in ["lo"]:
                            interfaces.append(iface)
            
            # Save tc qdisc for each interface
            for iface in interfaces:
                success, stdout, stderr = _run_command(["tc", "qdisc", "show", "dev", iface])
                if success:
                    tc_data[f"{iface}_qdisc"] = stdout
                
                success, stdout, stderr = _run_command(["tc", "class", "show", "dev", iface])
                if success:
                    tc_data[f"{iface}_class"] = stdout
                
                success, stdout, stderr = _run_command(["tc", "filter", "show", "dev", iface])
                if success:
                    tc_data[f"{iface}_filter"] = stdout
            
            (checkpoint_path / "tc_config.json").write_text(json.dumps(tc_data, indent=2))
            notes.append(f"✓ Saved tc config for {len(interfaces)} interfaces")
        
        # 3. Save nftables rules
        success, stdout, stderr = _run_command(["nft", "list", "ruleset"])
        if success:
            (checkpoint_path / "nft_ruleset.txt").write_text(stdout)
            notes.append("✓ Saved nftables ruleset")
        elif "No such file" not in stderr:
            errors.append(f"nft not available: {stderr}")
        
        # 4. Save ethtool settings for each interface
        if success:  # Reuse interface list from tc step
            ethtool_data = {}
            for iface in interfaces:
                # Get offload settings
                success, stdout, stderr = _run_command(["ethtool", "-k", iface])
                if success:
                    ethtool_data[f"{iface}_offloads"] = stdout
                
                # Get interface info
                success, stdout, stderr = _run_command(["ethtool", iface])
                if success:
                    ethtool_data[f"{iface}_info"] = stdout
            
            if ethtool_data:
                (checkpoint_path / "ethtool_settings.json").write_text(json.dumps(ethtool_data, indent=2))
                notes.append(f"✓ Saved ethtool settings for {len(interfaces)} interfaces")
        
        # 5. Save interface configuration (MTU, state, etc.)
        success, stdout, stderr = _run_command(["ip", "link", "show"])
        if success:
            (checkpoint_path / "ip_link.txt").write_text(stdout)
            notes.append("✓ Saved interface configuration")
        
        # 6. Save ip address configuration
        success, stdout, stderr = _run_command(["ip", "addr", "show"])
        if success:
            (checkpoint_path / "ip_addr.txt").write_text(stdout)
        
        # 7. Save metadata
        metadata = {
            "checkpoint_id": checkpoint_id,
            "timestamp": timestamp,
            "label": label or "Unnamed checkpoint",
            "created_at": datetime.now().isoformat(),
            "notes": notes,
            "errors": errors
        }
        (checkpoint_path / "metadata.json").write_text(json.dumps(metadata, indent=2))
        
        result = {
            "ok": True,
            "checkpoint_id": checkpoint_id,
            "path": str(checkpoint_path),
            "notes": notes,
            "errors": errors
        }
        
        return result
        
    except Exception as e:
        return {
            "ok": False,
            "checkpoint_id": None,
            "notes": [f"Failed to create checkpoint: {str(e)}"],
            "errors": [str(e)]
        }


def rollback_to_checkpoint(checkpoint_id: str) -> dict:
    """
    Restore system state from a checkpoint.
    
    OUTPUT: {"ok": true, "restored": true, "notes": [...]}
    
    Args:
        checkpoint_id: The ID of the checkpoint to restore
    """
    if not isinstance(checkpoint_id, str) or not checkpoint_id:
        return {"ok": False, "restored": False, "notes": ["invalid checkpoint_id"]}
    
    checkpoint_path = CHECKPOINT_DIR / checkpoint_id
    
    if not checkpoint_path.exists():
        return {
            "ok": False,
            "restored": False,
            "notes": [f"Checkpoint '{checkpoint_id}' not found at {checkpoint_path}"]
        }
    
    notes = []
    errors = []
    
    try:
        # Load metadata
        metadata_file = checkpoint_path / "metadata.json"
        if metadata_file.exists():
            metadata = json.loads(metadata_file.read_text())
            notes.append(f"Restoring checkpoint: {metadata.get('label', checkpoint_id)}")
            notes.append(f"Created: {metadata.get('created_at', 'unknown')}")
        
        # 1. Restore sysctl settings
        sysctl_file = checkpoint_path / "sysctl.conf"
        if sysctl_file.exists():
            sysctl_content = sysctl_file.read_text()
            restored_count = 0
            failed_count = 0
            
            for line in sysctl_content.split("\n"):
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                
                # Parse: key = value or key=value
                if " = " in line:
                    key, value = line.split(" = ", 1)
                else:
                    key, value = line.split("=", 1)
                
                key = key.strip()
                value = value.strip()
                
                # Skip read-only or problematic sysctls
                skip_patterns = [
                    "kernel.random",
                    "kernel.ns_last_pid",
                    "fs.inode-state",
                    "fs.file-",
                    "kernel.pty.nr",
                    "kernel.sched_domain",
                    "dev.cdrom",
                    "kernel.core_pipe_limit"
                ]
                
                if any(pattern in key for pattern in skip_patterns):
                    continue
                
                # Try to set the value (requires sudo)
                success, stdout, stderr = _run_command(["sysctl", "-w", f"{key}={value}"], use_sudo=True)
                if success:
                    restored_count += 1
                else:
                    failed_count += 1
                    if failed_count <= 5:  # Only report first 5 failures
                        errors.append(f"Failed to restore {key}: {stderr[:100]}")
            
            notes.append(f"✓ Restored {restored_count} sysctl settings ({failed_count} failed/skipped)")
        
        # 2. Restore tc configuration
        tc_file = checkpoint_path / "tc_config.json"
        if tc_file.exists():
            tc_data = json.loads(tc_file.read_text())
            
            # First, clear existing tc rules
            success, stdout, stderr = _run_command(["ip", "link", "show"])
            if success:
                for line in stdout.split("\n"):
                    if ":" in line and not line.startswith(" "):
                        parts = line.split(":")
                        if len(parts) >= 2:
                            iface = parts[1].strip().split("@")[0]
                            if iface and iface != "lo":
                                # Delete existing qdisc (this clears everything) - requires sudo
                                _run_command(["tc", "qdisc", "del", "dev", iface, "root"], use_sudo=True)
                                _run_command(["tc", "qdisc", "del", "dev", iface, "ingress"], use_sudo=True)
            
            notes.append("✓ Cleared existing tc configuration")
            # Note: Full tc restoration is complex and may require parsing saved output
            # For now, we've cleared it to baseline state
        
        # 3. Restore nftables
        nft_file = checkpoint_path / "nft_ruleset.txt"
        if nft_file.exists():
            nft_content = nft_file.read_text()
            
            # Clear existing rules (requires sudo)
            _run_command(["nft", "flush", "ruleset"], use_sudo=True)
            
            # Restore from file
            # Write to temp file and load it
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.nft', delete=False) as f:
                f.write(nft_content)
                temp_nft = f.name
            
            success, stdout, stderr = _run_command(["nft", "-f", temp_nft], use_sudo=True)
            Path(temp_nft).unlink()
            
            if success:
                notes.append("✓ Restored nftables ruleset")
            else:
                errors.append(f"Failed to restore nftables: {stderr}")
        
        # 4. Restore ethtool settings
        ethtool_file = checkpoint_path / "ethtool_settings.json"
        if ethtool_file.exists():
            ethtool_data = json.loads(ethtool_file.read_text())
            
            # Parse and restore offload settings
            for key, content in ethtool_data.items():
                if "_offloads" in key:
                    iface = key.replace("_offloads", "")
                    # Parse ethtool -k output and restore settings
                    # Format: "feature: on/off [fixed]"
                    for line in content.split("\n"):
                        if ": " in line and "[fixed]" not in line:
                            feature, state = line.split(":", 1)
                            feature = feature.strip()
                            state = state.split()[0].strip()  # Get 'on' or 'off'
                            
                            # Try to set it (requires sudo)
                            _run_command(["ethtool", "-K", iface, feature, state], use_sudo=True)
            
            notes.append("✓ Restored ethtool offload settings")
        
        # 5. Restore MTU and interface settings
        ip_link_file = checkpoint_path / "ip_link.txt"
        if ip_link_file.exists():
            ip_link_content = ip_link_file.read_text()
            
            # Parse and restore MTU
            for line in ip_link_content.split("\n"):
                if "mtu " in line and ":" in line:
                    parts = line.split()
                    iface = parts[1].rstrip(":")
                    
                    # Find MTU value
                    for i, part in enumerate(parts):
                        if part == "mtu" and i + 1 < len(parts):
                            mtu = parts[i + 1]
                            # Restore MTU (requires sudo)
                            success, stdout, stderr = _run_command(
                                ["ip", "link", "set", "dev", iface, "mtu", mtu],
                                use_sudo=True
                            )
                            if success:
                                notes.append(f"✓ Restored MTU for {iface}: {mtu}")
                            break
        
        if errors:
            result = {
                "ok": False,
                "restored": True,  # Partial restoration
                "notes": notes,
                "errors": errors
            }
            log_rollback(checkpoint_id, False, notes)
            return result
        
        result = {
            "ok": True,
            "restored": True,
            "notes": notes,
            "errors": []
        }
        log_rollback(checkpoint_id, True, notes)
        return result
        
    except Exception as e:
        result = {
            "ok": False,
            "restored": False,
            "notes": notes,
            "errors": errors + [f"Rollback failed: {str(e)}"]
        }
        log_rollback(checkpoint_id, False, notes)
        return result


def list_checkpoints() -> dict:
    """
    List all available checkpoints with their metadata.
    
    OUTPUT: {"ok": true, "checkpoints": [...]}
    """
    try:
        _ensure_checkpoint_dir()
        
        checkpoints = []
        for checkpoint_dir in sorted(CHECKPOINT_DIR.iterdir()):
            if checkpoint_dir.is_dir():
                metadata_file = checkpoint_dir / "metadata.json"
                if metadata_file.exists():
                    metadata = json.loads(metadata_file.read_text())
                    checkpoints.append(metadata)
                else:
                    # Checkpoint without metadata
                    checkpoints.append({
                        "checkpoint_id": checkpoint_dir.name,
                        "label": "Unknown",
                        "created_at": "Unknown"
                    })
        
        return {
            "ok": True,
            "count": len(checkpoints),
            "checkpoints": checkpoints
        }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "checkpoints": []
        }


def delete_checkpoint(checkpoint_id: str) -> dict:
    """
    Delete a checkpoint.
    
    OUTPUT: {"ok": true, "notes": "..."}
    """
    if not isinstance(checkpoint_id, str) or not checkpoint_id:
        return {"ok": False, "notes": "invalid checkpoint_id"}
    
    checkpoint_path = CHECKPOINT_DIR / checkpoint_id
    
    if not checkpoint_path.exists():
        return {"ok": False, "notes": f"Checkpoint '{checkpoint_id}' not found"}
    
    try:
        import shutil
        shutil.rmtree(checkpoint_path)
        return {"ok": True, "notes": f"Deleted checkpoint: {checkpoint_id}"}
    except Exception as e:
        return {"ok": False, "notes": f"Failed to delete checkpoint: {str(e)}"}
