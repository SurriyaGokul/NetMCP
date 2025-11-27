import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

AUDIT_DIR = Path.home() / ".mcp-net-optimizer" / "audit_logs"
CURRENT_LOG = AUDIT_DIR / "current.log"
AUDIT_JSON = AUDIT_DIR / "audit_log.json"


def _ensure_audit_dir():
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)


def _rotate_log_if_needed():
    if CURRENT_LOG.exists() and CURRENT_LOG.stat().st_size > 10 * 1024 * 1024:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        archive_name = AUDIT_DIR / f"audit_{timestamp}.log"
        CURRENT_LOG.rename(archive_name)


class AuditLogger:
    def __init__(self):
        _ensure_audit_dir()
        _rotate_log_if_needed()
        
        # Setup text logger
        self.logger = logging.getLogger("mcp_net_optimizer_audit")
        self.logger.setLevel(logging.INFO)
        
        # Remove existing handlers to avoid duplicates
        self.logger.handlers.clear()
        
        # File handler for text logs
        file_handler = logging.FileHandler(CURRENT_LOG, mode='a')
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # Prevent propagation to root logger
        self.logger.propagate = False
    
    def log_plan_validation(self, plan: Dict, validation_result: Dict):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": "validate_plan",
            "plan_interface": plan.get("iface"),
            "plan_profile": plan.get("profile"),
            "validation_ok": validation_result.get("ok"),
            "validation_issues": validation_result.get("issues", []),
        }
        
        self._write_json_entry(entry)
        
        status = "PASSED" if validation_result.get("ok") else "FAILED"
        self.logger.info(
            f"Plan Validation {status} | Interface: {plan.get('iface')} | "
            f"Profile: {plan.get('profile')} | Issues: {len(validation_result.get('issues', []))}"
        )
    
    def log_plan_rendering(self, plan: Dict, rendered_plan: Dict):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": "render_plan",
            "plan_interface": plan.get("iface"),
            "plan_profile": plan.get("profile"),
            "sysctl_count": len(rendered_plan.get("sysctl_cmds", [])),
            "has_tc_script": bool(rendered_plan.get("tc_script")),
            "has_nft_script": bool(rendered_plan.get("nft_script")),
        }
        
        self._write_json_entry(entry)
        
        self.logger.info(
            f"Plan Rendered | Interface: {plan.get('iface')} | Profile: {plan.get('profile')} | "
            f"Sysctl: {len(rendered_plan.get('sysctl_cmds', []))} commands | "
            f"TC: {'yes' if rendered_plan.get('tc_script') else 'no'} | "
            f"NFT: {'yes' if rendered_plan.get('nft_script') else 'no'}"
        )
    
    def log_checkpoint_creation(self, checkpoint_id: str, label: Optional[str] = None):
        """Log creation of a system checkpoint."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": "create_checkpoint",
            "checkpoint_id": checkpoint_id,
            "label": label or "Unnamed"
        }
        
        self._write_json_entry(entry)
        
        self.logger.info(f"Checkpoint Created | ID: {checkpoint_id} | Label: {label or 'Unnamed'}")
    
    def log_command_execution(
        self, 
        command: List[str], 
        success: bool, 
        stdout: str = "", 
        stderr: str = "",
        checkpoint_id: Optional[str] = None
    ):
        """Log execution of a system command."""
        cmd_str = " ".join(command)
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": "execute_command",
            "command": cmd_str,
            "success": success,
            "stdout": stdout[:500] if stdout else "",  # Truncate long output
            "stderr": stderr[:500] if stderr else "",
            "checkpoint_id": checkpoint_id
        }
        
        self._write_json_entry(entry)
        
        status = "✓" if success else "✗"
        self.logger.info(
            f"Command {status} | {cmd_str} | Checkpoint: {checkpoint_id or 'N/A'}"
        )
        
        if not success and stderr:
            self.logger.error(f"Command Failed | {cmd_str} | Error: {stderr[:200]}")
    
    def log_plan_application(
        self,
        rendered_plan: Dict,
        change_report: Dict,
        checkpoint_id: Optional[str] = None
    ):
        """Log application of a rendered plan."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": "apply_plan",
            "checkpoint_id": checkpoint_id,
            "applied": change_report.get("applied"),
            "dry_run": change_report.get("dry_run"),
            "errors": change_report.get("errors", []),
            "sysctl_commands": rendered_plan.get("sysctl_cmds", []),
            "tc_script_lines": len(rendered_plan.get("tc_script", "").splitlines()),
            "nft_script_lines": len(rendered_plan.get("nft_script", "").splitlines()),
            "notes": change_report.get("notes", [])
        }
        
        self._write_json_entry(entry)
        
        status = "SUCCESS" if change_report.get("applied") else "FAILED"
        error_count = len(change_report.get("errors", []))
        
        self.logger.info(
            f"Plan Application {status} | Checkpoint: {checkpoint_id or 'N/A'} | "
            f"Errors: {error_count} | Dry Run: {change_report.get('dry_run')}"
        )
        
        # Log each note from the change report
        for note in change_report.get("notes", []):
            self.logger.info(f"  {note}")
        
        # Log errors if any
        for error in change_report.get("errors", []):
            self.logger.error(f"  ERROR: {error}")
    
    def log_rollback(self, checkpoint_id: str, success: bool, notes: List[str] = None):
        """Log rollback to a checkpoint."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": "rollback",
            "checkpoint_id": checkpoint_id,
            "success": success,
            "notes": notes or []
        }
        
        self._write_json_entry(entry)
        
        status = "SUCCESS" if success else "FAILED"
        self.logger.info(f"Rollback {status} | Checkpoint: {checkpoint_id}")
        
        if notes:
            for note in notes:
                self.logger.info(f"  {note}")
    
    def log_validation_test(
        self,
        profile: str,
        before_results: Dict,
        after_results: Dict,
        validation_decision: str,
        score: int
    ):
        """Log validation test comparing before/after performance."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": "validation_test",
            "profile": profile,
            "decision": validation_decision,
            "score": score,
            "before_available": before_results.get("tests", {}).get("latency", {}).get("available", False),
            "after_available": after_results.get("tests", {}).get("latency", {}).get("available", False)
        }
        
        self._write_json_entry(entry)
        
        self.logger.info(
            f"Validation Test | Profile: {profile} | Decision: {validation_decision} | Score: {score}/100"
        )
    
    def _write_json_entry(self, entry: Dict):
        """Write an entry to the JSON audit log."""
        try:
            # Read existing entries
            if AUDIT_JSON.exists():
                try:
                    with open(AUDIT_JSON, 'r') as f:
                        entries = json.load(f)
                except json.JSONDecodeError:
                    entries = []
            else:
                entries = []
            
            # Append new entry
            entries.append(entry)
            
            # Write back to file
            with open(AUDIT_JSON, 'w') as f:
                json.dump(entries, f, indent=2)
        
        except Exception as e:
            # Don't let logging failures break the application
            self.logger.error(f"Failed to write JSON audit entry: {e}")
    
    def get_recent_entries(self, limit: int = 50) -> List[Dict]:
        """Get recent audit log entries."""
        if not AUDIT_JSON.exists():
            return []
        
        try:
            with open(AUDIT_JSON, 'r') as f:
                entries = json.load(f)
            return entries[-limit:] if len(entries) > limit else entries
        except Exception as e:
            self.logger.error(f"Failed to read audit log: {e}")
            return []
    
    def search_entries(
        self,
        action: Optional[str] = None,
        checkpoint_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict]:
        """Search audit log entries by criteria."""
        if not AUDIT_JSON.exists():
            return []
        
        try:
            with open(AUDIT_JSON, 'r') as f:
                entries = json.load(f)
            
            filtered = entries
            
            if action:
                filtered = [e for e in filtered if e.get("action") == action]
            
            if checkpoint_id:
                filtered = [e for e in filtered if e.get("checkpoint_id") == checkpoint_id]
            
            if start_date:
                filtered = [e for e in filtered if e.get("timestamp", "") >= start_date]
            
            if end_date:
                filtered = [e for e in filtered if e.get("timestamp", "") <= end_date]
            
            return filtered
        
        except Exception as e:
            self.logger.error(f"Failed to search audit log: {e}")
            return []


# Global singleton instance
_audit_logger = None


def get_audit_logger() -> AuditLogger:
    """Get the global audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


def log_plan_validation(plan: Dict, validation_result: Dict):
    """Convenience function for logging plan validation."""
    get_audit_logger().log_plan_validation(plan, validation_result)


def log_plan_rendering(plan: Dict, rendered_plan: Dict):
    """Convenience function for logging plan rendering."""
    get_audit_logger().log_plan_rendering(plan, rendered_plan)


def log_checkpoint_creation(checkpoint_id: str, label: Optional[str] = None):
    """Convenience function for logging checkpoint creation."""
    get_audit_logger().log_checkpoint_creation(checkpoint_id, label)


def log_command_execution(
    command: List[str],
    success: bool,
    stdout: str = "",
    stderr: str = "",
    checkpoint_id: Optional[str] = None
):
    """Convenience function for logging command execution."""
    get_audit_logger().log_command_execution(command, success, stdout, stderr, checkpoint_id)


def log_plan_application(
    rendered_plan: Dict,
    change_report: Dict,
    checkpoint_id: Optional[str] = None
):
    """Convenience function for logging plan application."""
    get_audit_logger().log_plan_application(rendered_plan, change_report, checkpoint_id)


def log_rollback(checkpoint_id: str, success: bool, notes: List[str] = None):
    """Convenience function for logging rollback."""
    get_audit_logger().log_rollback(checkpoint_id, success, notes)


def log_validation_test(
    profile: str,
    before_results: Dict,
    after_results: Dict,
    validation_decision: str,
    score: int
):
    """Convenience function for logging validation tests."""
    get_audit_logger().log_validation_test(profile, before_results, after_results, validation_decision, score)
