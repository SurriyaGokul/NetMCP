#!/usr/bin/env python3
"""
Test audit logging functionality.
"""

import sys
import json
from pathlib import Path

# Add server directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.audit_log import (
    get_audit_logger,
    log_plan_validation,
    log_plan_rendering,
    log_checkpoint_creation,
    log_command_execution,
    log_plan_application,
    log_rollback,
    log_validation_test
)


def test_audit_logging():
    """Test all audit logging functions."""
    
    print("Testing Audit Logging System")
    print("=" * 60)
    
    # Test 1: Plan validation logging
    print("\n1. Testing plan validation logging...")
    plan = {
        "iface": "eth0",
        "profile": "gaming",
        "changes": {}
    }
    validation_result = {
        "ok": True,
        "issues": []
    }
    log_plan_validation(plan, validation_result)
    print("✓ Plan validation logged")
    
    # Test 2: Plan rendering logging
    print("\n2. Testing plan rendering logging...")
    rendered_plan = {
        "sysctl_cmds": ["sysctl -w net.ipv4.tcp_congestion_control=bbr"],
        "tc_script": "tc qdisc add dev eth0 root fq",
        "nft_script": ""
    }
    log_plan_rendering(plan, rendered_plan)
    print("✓ Plan rendering logged")
    
    # Test 3: Checkpoint creation logging
    print("\n3. Testing checkpoint creation logging...")
    checkpoint_id = "checkpoint-20251111-120000"
    log_checkpoint_creation(checkpoint_id, "Test checkpoint")
    print("✓ Checkpoint creation logged")
    
    # Test 4: Command execution logging
    print("\n4. Testing command execution logging...")
    log_command_execution(
        ["sysctl", "-w", "net.ipv4.tcp_congestion_control=bbr"],
        True,
        "net.ipv4.tcp_congestion_control = bbr",
        "",
        checkpoint_id
    )
    print("✓ Command execution logged")
    
    # Test 5: Plan application logging
    print("\n5. Testing plan application logging...")
    change_report = {
        "applied": True,
        "dry_run": False,
        "errors": [],
        "notes": ["✓ All changes applied successfully"]
    }
    log_plan_application(rendered_plan, change_report, checkpoint_id)
    print("✓ Plan application logged")
    
    # Test 6: Rollback logging
    print("\n6. Testing rollback logging...")
    log_rollback(checkpoint_id, True, ["✓ Rollback completed successfully"])
    print("✓ Rollback logged")
    
    # Test 7: Validation test logging
    print("\n7. Testing validation test logging...")
    before_results = {
        "tests": {
            "latency": {
                "available": True,
                "avg_ms": 20.5
            }
        }
    }
    after_results = {
        "tests": {
            "latency": {
                "available": True,
                "avg_ms": 18.2
            }
        }
    }
    log_validation_test("gaming", before_results, after_results, "KEEP", 75)
    print("✓ Validation test logged")
    
    # Test 8: Retrieve recent entries
    print("\n8. Testing audit log retrieval...")
    logger = get_audit_logger()
    entries = logger.get_recent_entries(limit=10)
    print(f"✓ Retrieved {len(entries)} recent entries")
    
    # Test 9: Search entries
    print("\n9. Testing audit log search...")
    search_results = logger.search_entries(action="validate_plan")
    print(f"✓ Found {len(search_results)} validation entries")
    
    # Display summary
    print("\n" + "=" * 60)
    print("AUDIT LOG SUMMARY")
    print("=" * 60)
    
    all_entries = logger.get_recent_entries(limit=100)
    action_counts = {}
    for entry in all_entries:
        action = entry.get("action", "unknown")
        action_counts[action] = action_counts.get(action, 0) + 1
    
    print(f"\nTotal entries: {len(all_entries)}")
    print("\nEntries by action type:")
    for action, count in sorted(action_counts.items()):
        print(f"  {action}: {count}")
    
    # Show last 5 entries
    print("\nLast 5 entries:")
    for entry in entries[-5:]:
        timestamp = entry.get("timestamp", "unknown")
        action = entry.get("action", "unknown")
        print(f"  {timestamp} - {action}")
    
    print("\n" + "=" * 60)
    print("✓ All audit logging tests passed!")
    print("=" * 60)
    
    # Print log file locations
    from tools.audit_log import AUDIT_DIR, CURRENT_LOG, AUDIT_JSON
    print(f"\nAudit logs are stored in:")
    print(f"  Directory: {AUDIT_DIR}")
    print(f"  Text log: {CURRENT_LOG}")
    print(f"  JSON log: {AUDIT_JSON}")
    
    return True


if __name__ == "__main__":
    try:
        success = test_audit_logging()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
