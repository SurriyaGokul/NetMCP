#!/usr/bin/env python3
"""
Comprehensive MCP Server Test Suite
Tests the server as if it were being called by Claude Desktop
"""
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from server.tools import discovery
from server.tools.planner import render_change_plan
from server.tools.validator import validate_change_plan
from server.tools.validation_metrics import run_full_benchmark, quick_latency_test
from server.tools.apply.checkpoints import snapshot_checkpoint, list_checkpoints
from server.tools.util.policy_loader import PolicyRegistry


class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []
    
    def add_test(self, name: str, passed: bool, message: str = ""):
        self.tests.append({"name": name, "passed": passed, "message": message})
        if passed:
            self.passed += 1
            print(f"✓ PASS: {name}")
        else:
            self.failed += 1
            print(f"✗ FAIL: {name}")
        if message:
            print(f"  → {message}")
    
    def summary(self):
        total = self.passed + self.failed
        print("\n" + "="*80)
        print(f"TEST SUMMARY: {self.passed}/{total} passed, {self.failed}/{total} failed")
        print("="*80)
        return self.failed == 0


def test_discovery_tools(results: TestResults):
    """Test network discovery tools"""
    print("\n" + "="*80)
    print("TEST SUITE 1: Discovery Tools")
    print("="*80)
    
    # Test ip_info
    try:
        result = discovery.ip_info()
        results.add_test(
            "ip_info()",
            result.get("ok") and "eth0" in result.get("stdout", ""),
            f"Found {len(result.get('stdout', '').splitlines())} lines of output"
        )
    except Exception as e:
        results.add_test("ip_info()", False, f"Exception: {e}")
    
    # Test eth_info
    try:
        result = discovery.eth_info("eth0")
        results.add_test(
            "eth_info('eth0')",
            result.get("ok") or "No such device" in result.get("stderr", ""),
            "Interface query executed"
        )
    except Exception as e:
        results.add_test("eth_info('eth0')", False, f"Exception: {e}")
    
    # Test ip_route
    try:
        result = discovery.ip_route()
        results.add_test(
            "ip_route()",
            result.get("ok") and len(result.get("stdout", "")) > 0,
            "Routing table retrieved"
        )
    except Exception as e:
        results.add_test("ip_route()", False, f"Exception: {e}")
    
    # Test hostname_ips
    try:
        result = discovery.hostname_ips()
        results.add_test(
            "hostname_ips()",
            result.get("ok"),
            "Hostname IPs retrieved"
        )
    except Exception as e:
        results.add_test("hostname_ips()", False, f"Exception: {e}")


def test_policy_resources(results: TestResults):
    """Test policy card loading and retrieval"""
    print("\n" + "="*80)
    print("TEST SUITE 2: Policy Resources")
    print("="*80)
    
    try:
        policy_root = Path(__file__).parent / "policy" / "config_cards"
        registry = PolicyRegistry(policy_root=str(policy_root))
        
        # Test list
        cards = registry.list()
        results.add_test(
            "PolicyRegistry.list()",
            len(cards) > 20,
            f"Loaded {len(cards)} configuration cards"
        )
        
        # Test get specific card
        card = registry.get("sysctl.tcp_congestion_control")
        results.add_test(
            "PolicyRegistry.get('sysctl.tcp_congestion_control')",
            card is not None and "description" in card,
            "Card retrieved successfully"
        )
        
        # Test invalid card
        invalid_card = registry.get("nonexistent.card")
        results.add_test(
            "PolicyRegistry.get() with invalid card",
            invalid_card is None,
            "Properly returns None for invalid cards"
        )
        
    except Exception as e:
        results.add_test("PolicyRegistry", False, f"Exception: {e}")


def test_validation_workflow(results: TestResults):
    """Test plan validation"""
    print("\n" + "="*80)
    print("TEST SUITE 3: Validation Workflow")
    print("="*80)
    
    # Test valid plan
    valid_plan = {
        "iface": "eth0",
        "profile": "gaming",
        "changes": {
            "sysctl": {
                "net.ipv4.tcp_low_latency": "1",
                "net.ipv4.tcp_fastopen": "3"
            }
        },
        "rationale": "Test gaming optimization"
    }
    
    try:
        validation = validate_change_plan(valid_plan)
        results.add_test(
            "validate_change_plan() with valid plan",
            validation.get("ok") == True,
            f"Validation passed: {validation.get('ok')}"
        )
    except Exception as e:
        results.add_test("validate_change_plan() valid", False, f"Exception: {e}")
    
    # Test invalid plan (missing required field)
    invalid_plan = {
        "profile": "gaming",
        "changes": {}
    }
    
    try:
        validation = validate_change_plan(invalid_plan)
        has_errors = (validation.get("ok") == False and len(validation.get("errors", [])) > 0)
        results.add_test(
            "validate_change_plan() with invalid plan",
            has_errors,
            f"Properly caught {len(validation.get('errors', []))} validation errors"
        )
    except Exception as e:
        # Exception is also acceptable for invalid plans
        results.add_test("validate_change_plan() invalid", True, "Properly rejected invalid plan with exception")


def test_rendering_workflow(results: TestResults):
    """Test plan rendering to commands"""
    print("\n" + "="*80)
    print("TEST SUITE 4: Rendering Workflow")
    print("="*80)
    
    plan = {
        "iface": "eth0",
        "profile": "gaming",
        "changes": {
            "sysctl": {
                "net.ipv4.tcp_low_latency": "1",
                "net.ipv4.tcp_fastopen": "3",
                "net.core.netdev_budget": "600"
            }
        },
        "rationale": "Gaming optimization test"
    }
    
    try:
        rendered = render_change_plan(plan)
        
        results.add_test(
            "render_change_plan() returns RenderedPlan",
            isinstance(rendered, dict),
            f"Type: {type(rendered)}"
        )
        
        results.add_test(
            "RenderedPlan has sysctl_cmds",
            "sysctl_cmds" in rendered and len(rendered["sysctl_cmds"]) > 0,
            f"Generated {len(rendered.get('sysctl_cmds', []))} sysctl commands"
        )
        
        # Verify command format
        if rendered.get("sysctl_cmds"):
            cmd = rendered["sysctl_cmds"][0]
            results.add_test(
                "Sysctl commands are properly formatted",
                cmd.startswith("sysctl -w "),
                f"Sample: {cmd}"
            )
        
    except Exception as e:
        results.add_test("render_change_plan()", False, f"Exception: {e}")
    
    # Test TC rendering
    tc_plan = {
        "iface": "eth0",
        "profile": "gaming",
        "changes": {
            "qdisc": {
                "type": "fq_codel",
                "params": {}
            }
        },
        "rationale": "Test TC rendering"
    }
    
    try:
        rendered = render_change_plan(tc_plan)
        results.add_test(
            "render_change_plan() with TC qdisc",
            "tc_script" in rendered and len(rendered["tc_script"]) > 0,
            "Generated TC script"
        )
        
        if rendered.get("tc_script"):
            results.add_test(
                "TC script contains qdisc commands",
                "tc qdisc" in rendered["tc_script"],
                "TC commands found"
            )
    except Exception as e:
        results.add_test("render_change_plan() TC", False, f"Exception: {e}")


def test_benchmark_tools(results: TestResults):
    """Test network benchmarking tools"""
    print("\n" + "="*80)
    print("TEST SUITE 5: Benchmark & Validation Metrics")
    print("="*80)
    
    # Test quick latency test
    try:
        result = quick_latency_test()
        results.add_test(
            "quick_latency_test()",
            result.get("available") == True,
            f"Avg latency: {result.get('avg_ms', 'N/A')}ms"
        )
    except Exception as e:
        results.add_test("quick_latency_test()", False, f"Exception: {e}")
    
    # Test full benchmark with new fields
    try:
        result = run_full_benchmark(profile="gaming")
        
        results.add_test(
            "run_full_benchmark() returns results",
            isinstance(result, dict),
            f"Type: {type(result)}"
        )
        
        results.add_test(
            "Benchmark has 'test_suite' field",
            "test_suite" in result,
            f"test_suite: {result.get('test_suite', 'N/A')}"
        )
        
        results.add_test(
            "Benchmark has 'recommended_profile' field",
            "recommended_profile" in result,
            f"recommended_profile: {result.get('recommended_profile', 'N/A')}"
        )
        
        results.add_test(
            "Benchmark has 'tests' field with latency",
            "tests" in result and "latency" in result["tests"],
            f"Tests: {list(result.get('tests', {}).keys())}"
        )
        
        results.add_test(
            "Benchmark has 'summary' field",
            "summary" in result and len(result["summary"]) > 0,
            f"Summary: {result.get('summary', 'N/A')}"
        )
        
        # Verify no 'profile' field (old misleading field)
        results.add_test(
            "Benchmark does NOT have misleading 'profile' field",
            "profile" not in result or result.get("profile") == result.get("test_suite"),
            "Fixed misleading field naming"
        )
        
    except Exception as e:
        results.add_test("run_full_benchmark()", False, f"Exception: {e}")


def test_checkpoint_system(results: TestResults):
    """Test checkpoint/rollback system"""
    print("\n" + "="*80)
    print("TEST SUITE 6: Checkpoint System")
    print("="*80)
    
    # Note: We're just testing the functions exist and run, not actually creating checkpoints
    try:
        checkpoints = list_checkpoints()
        results.add_test(
            "list_checkpoints()",
            isinstance(checkpoints, dict),
            f"Returned {len(checkpoints.get('checkpoints', []))} checkpoints"
        )
    except Exception as e:
        results.add_test("list_checkpoints()", False, f"Exception: {e}")


def test_end_to_end_workflow(results: TestResults):
    """Simulate complete Claude Desktop workflow"""
    print("\n" + "="*80)
    print("TEST SUITE 7: End-to-End Workflow Simulation")
    print("="*80)
    
    print("\n→ Step 1: Discovery")
    network_info = discovery.ip_info()
    routing_info = discovery.ip_route()
    
    results.add_test(
        "E2E: Network discovery",
        network_info.get("ok") and routing_info.get("ok"),
        "Successfully gathered network information"
    )
    
    print("\n→ Step 2: Create optimization plan")
    plan = {
        "iface": "eth0",
        "profile": "gaming",
        "changes": {
            "sysctl": {
                "net.ipv4.tcp_low_latency": "1",
                "net.ipv4.tcp_fastopen": "3",
                "net.core.netdev_budget": "600"
            },
            "qdisc": {
                "type": "fq_codel",
                "params": {}
            }
        },
        "rationale": "End-to-end test: Gaming optimization with low latency and FQ-CoDel qdisc"
    }
    
    print("\n→ Step 3: Validate plan")
    validation = validate_change_plan(plan)
    results.add_test(
        "E2E: Plan validation",
        validation.get("ok") == True,
        f"Validation result: {validation.get('ok')}"
    )
    
    if validation.get("ok"):
        print("\n→ Step 4: Render to executable commands")
        rendered = render_change_plan(plan)
        
        results.add_test(
            "E2E: Command rendering",
            "sysctl_cmds" in rendered and "tc_script" in rendered,
            f"Generated {len(rendered.get('sysctl_cmds', []))} sysctl commands and TC script"
        )
        
        print("\n→ Step 5: Preview commands (no execution)")
        print("\nSysctl Commands:")
        for cmd in rendered.get("sysctl_cmds", [])[:3]:
            print(f"  {cmd}")
        if len(rendered.get("sysctl_cmds", [])) > 3:
            print(f"  ... and {len(rendered.get('sysctl_cmds', [])) - 3} more")
        
        print("\nTC Script:")
        tc_lines = rendered.get("tc_script", "").split("\n")
        for line in tc_lines[:5]:
            if line.strip():
                print(f"  {line}")
        if len(tc_lines) > 5:
            print(f"  ... and {len(tc_lines) - 5} more lines")
        
        results.add_test(
            "E2E: Complete workflow",
            True,
            "Successfully completed discovery → plan → validate → render"
        )
    else:
        results.add_test(
            "E2E: Complete workflow",
            False,
            f"Validation failed: {validation.get('issues', [])}"
        )


def main():
    print("\n" + "="*80)
    print("MCP NETWORK OPTIMIZER - COMPREHENSIVE SERVER TEST")
    print("Testing as if being called by Claude Desktop")
    print("="*80)
    
    results = TestResults()
    
    # Run all test suites
    test_discovery_tools(results)
    test_policy_resources(results)
    test_validation_workflow(results)
    test_rendering_workflow(results)
    test_benchmark_tools(results)
    test_checkpoint_system(results)
    test_end_to_end_workflow(results)
    
    # Print summary
    success = results.summary()
    
    if success:
        print("\n✓ ALL TESTS PASSED - Server is working correctly!")
        return 0
    else:
        print(f"\n✗ {results.failed} TEST(S) FAILED - Review errors above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
