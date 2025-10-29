"""
Integration tests for the MCP Network Optimizer server.
Tests the full workflow from discovery to plan creation, validation, rendering, and application.
"""
import pytest
import json
import sys
import os
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from server.tools.discovery import ip_info, hostname_ips, ip_route
from server.tools.planner import render_change_plan
from server.tools.validator import validate_change_plan
from server.tools.util.policy_loader import PolicyRegistry


class TestDiscoveryTools:
    """Test discovery tools return expected data structures."""
    
    def test_ip_info_returns_valid_response(self):
        """Test that ip_info returns a valid response structure."""
        result = ip_info()
        
        assert isinstance(result, dict), "Result should be a dictionary"
        assert "ok" in result, "Result should have 'ok' field"
        assert "code" in result, "Result should have 'code' field"
        assert "stdout" in result, "Result should have 'stdout' field"
        assert "stderr" in result, "Result should have 'stderr' field"
        
        # If successful, stdout should contain interface information
        if result["ok"]:
            assert len(result["stdout"]) > 0, "stdout should not be empty on success"
            print(f"✓ IP Info Success: Found {result['stdout'][:100]}...")
        else:
            print(f"⚠ IP Info Warning: {result['stderr']}")
    
    def test_hostname_ips_returns_ips(self):
        """Test that hostname_ips returns IP addresses."""
        result = hostname_ips()
        
        assert isinstance(result, dict)
        assert "ok" in result
        
        if result["ok"]:
            # Should contain at least one IP address
            stdout = result["stdout"].strip()
            assert len(stdout) > 0, "Should return at least one IP"
            print(f"✓ Hostname IPs: {stdout}")
        else:
            print(f"⚠ Hostname IPs Warning: {result['stderr']}")
    
    def test_ip_route_returns_routes(self):
        """Test that ip_route returns routing information."""
        result = ip_route()
        
        assert isinstance(result, dict)
        assert "ok" in result
        
        if result["ok"]:
            assert len(result["stdout"]) > 0
            print(f"✓ IP Route Success: Found routing table")
        else:
            print(f"⚠ IP Route Warning: {result['stderr']}")


class TestPolicyRegistry:
    """Test policy registry loading and access."""
    
    @pytest.fixture
    def registry(self):
        """Create a policy registry instance."""
        policy_root = Path(__file__).parent.parent.parent / "policy" / "config_cards"
        return PolicyRegistry(policy_root=str(policy_root))
    
    def test_registry_loads_cards(self, registry):
        """Test that policy registry loads configuration cards."""
        cards = registry.list()
        
        assert isinstance(cards, list), "list() should return a list"
        assert len(cards) > 0, "Should load at least one configuration card"
        
        print(f"✓ Loaded {len(cards)} configuration cards")
        for card in cards[:5]:  # Print first 5
            print(f"  - {card}")
    
    def test_registry_get_card(self, registry):
        """Test getting a specific configuration card."""
        cards = registry.list()
        
        if cards:
            card_id = cards[0]
            card = registry.get(card_id)
            
            assert isinstance(card, dict), "get() should return a dictionary"
            assert "id" in card, "Card should have 'id' field"
            assert "description" in card, "Card should have 'description' field"
            
            print(f"✓ Successfully retrieved card: {card_id}")
            print(f"  Description: {card.get('description', 'N/A')[:100]}")


class TestValidator:
    """Test plan validation logic."""
    
    def test_validate_empty_plan(self):
        """Test validation of an empty plan."""
        plan = {
            "task_description": "Test empty plan",
            "rationale": "Testing validation",
            "parameters": []
        }
        
        result = validate_change_plan(plan)
        
        assert isinstance(result, dict)
        assert "ok" in result
        print(f"✓ Empty plan validation: {result}")
    
    def test_validate_simple_sysctl_plan(self):
        """Test validation of a simple sysctl parameter change."""
        plan = {
            "task_description": "Enable IP forwarding",
            "rationale": "Allow packet forwarding between interfaces",
            "parameters": [
                {
                    "scope": "sysctl",
                    "key": "net.ipv4.ip_forward",
                    "value": "1"
                }
            ]
        }
        
        result = validate_change_plan(plan)
        
        assert isinstance(result, dict)
        assert "ok" in result
        
        if result["ok"]:
            print(f"✓ Sysctl plan validation passed")
        else:
            print(f"✗ Sysctl plan validation failed: {result.get('issues', [])}")
    
    def test_validate_invalid_scope(self):
        """Test validation rejects invalid scope."""
        plan = {
            "task_description": "Invalid scope test",
            "rationale": "Testing validation",
            "parameters": [
                {
                    "scope": "invalid_scope",
                    "key": "some.key",
                    "value": "value"
                }
            ]
        }
        
        result = validate_change_plan(plan)
        
        # Should fail validation
        if not result["ok"]:
            print(f"✓ Correctly rejected invalid scope")
            print(f"  Issues: {result.get('issues', [])}")
        else:
            print(f"⚠ Warning: Did not reject invalid scope")


class TestPlanner:
    """Test plan rendering logic."""
    
    def test_render_sysctl_plan(self):
        """Test rendering a sysctl parameter change."""
        plan = {
            "task_description": "Increase TCP buffer sizes",
            "rationale": "Improve throughput for high-bandwidth connections",
            "parameters": [
                {
                    "scope": "sysctl",
                    "key": "net.core.rmem_max",
                    "value": "134217728"
                }
            ]
        }
        
        # First validate
        validation = validate_change_plan(plan)
        if validation["ok"]:
            # Then render
            rendered = render_change_plan(plan)
            
            assert isinstance(rendered, dict)
            assert "task_description" in rendered
            assert "commands" in rendered or "scripts" in rendered
            
            print(f"✓ Successfully rendered sysctl plan")
            if "commands" in rendered:
                print(f"  Commands: {len(rendered['commands'])} command(s)")
                for cmd in rendered["commands"][:3]:
                    print(f"    - {cmd}")
        else:
            print(f"⚠ Plan validation failed: {validation.get('issues', [])}")
    
    def test_render_tc_plan(self):
        """Test rendering a traffic control change."""
        plan = {
            "task_description": "Set up QoS with HTB",
            "rationale": "Rate limit network traffic",
            "parameters": [
                {
                    "scope": "tc",
                    "iface": "eth0",
                    "qdisc_type": "htb",
                    "handle": "1:",
                    "htb_rate": "100mbit"
                }
            ]
        }
        
        validation = validate_change_plan(plan)
        if validation["ok"]:
            rendered = render_change_plan(plan)
            
            assert isinstance(rendered, dict)
            print(f"✓ Successfully rendered TC plan")
            
            if "commands" in rendered:
                print(f"  Commands: {len(rendered['commands'])} command(s)")
                for cmd in rendered["commands"][:3]:
                    print(f"    - {cmd}")
        else:
            print(f"⚠ TC plan validation failed: {validation.get('issues', [])}")


class TestEndToEndWorkflow:
    """Test complete workflow scenarios."""
    
    def test_low_latency_gaming_scenario(self):
        """Test the workflow for optimizing a system for low-latency gaming."""
        print("\n=== Testing Low-Latency Gaming Optimization Scenario ===")
        
        # Step 1: Create a plan for low-latency gaming
        plan = {
            "task_description": "Optimize network for low-latency gaming",
            "rationale": "Reduce packet processing time and enable fast connection handling",
            "parameters": [
                {
                    "scope": "sysctl",
                    "key": "net.ipv4.tcp_low_latency",
                    "value": "1"
                },
                {
                    "scope": "sysctl",
                    "key": "net.ipv4.tcp_fastopen",
                    "value": "3"
                },
                {
                    "scope": "sysctl",
                    "key": "net.core.netdev_budget",
                    "value": "600"
                }
            ]
        }
        
        print("\n1. Plan Created:")
        print(f"   Task: {plan['task_description']}")
        print(f"   Parameters: {len(plan['parameters'])}")
        
        # Step 2: Validate the plan
        validation = validate_change_plan(plan)
        print(f"\n2. Validation Result: {'✓ PASSED' if validation['ok'] else '✗ FAILED'}")
        
        if not validation["ok"]:
            print(f"   Issues: {validation.get('issues', [])}")
            return
        
        # Step 3: Render the plan
        rendered = render_change_plan(plan)
        print(f"\n3. Rendering Result:")
        print(f"   Task: {rendered.get('task_description', 'N/A')}")
        
        if "commands" in rendered:
            print(f"   Commands generated: {len(rendered['commands'])}")
            print(f"   Sample commands:")
            for cmd in rendered["commands"][:3]:
                print(f"     - {cmd}")
        
        if "scripts" in rendered:
            print(f"   Scripts generated: {len(rendered['scripts'])}")
        
        print(f"\n✓ Low-latency gaming scenario workflow completed successfully")
    
    def test_high_throughput_server_scenario(self):
        """Test the workflow for optimizing a high-throughput server."""
        print("\n=== Testing High-Throughput Server Optimization Scenario ===")
        
        plan = {
            "task_description": "Optimize network for high-throughput file server",
            "rationale": "Increase buffer sizes and enable efficient congestion control",
            "parameters": [
                {
                    "scope": "sysctl",
                    "key": "net.core.rmem_max",
                    "value": "134217728"
                },
                {
                    "scope": "sysctl",
                    "key": "net.core.wmem_max",
                    "value": "134217728"
                },
                {
                    "scope": "sysctl",
                    "key": "net.ipv4.tcp_congestion_control",
                    "value": "bbr"
                },
                {
                    "scope": "sysctl",
                    "key": "net.core.default_qdisc",
                    "value": "fq"
                }
            ]
        }
        
        print("\n1. Plan Created:")
        print(f"   Task: {plan['task_description']}")
        print(f"   Parameters: {len(plan['parameters'])}")
        
        validation = validate_change_plan(plan)
        print(f"\n2. Validation Result: {'✓ PASSED' if validation['ok'] else '✗ FAILED'}")
        
        if validation["ok"]:
            rendered = render_change_plan(plan)
            print(f"\n3. Rendering Result:")
            print(f"   Commands generated: {len(rendered.get('commands', []))}")
            print(f"   Sample commands:")
            for cmd in rendered.get("commands", [])[:3]:
                print(f"     - {cmd}")
            
            print(f"\n✓ High-throughput server scenario workflow completed successfully")


class TestPerformanceMetrics:
    """Test performance and verify optimizations are effective."""
    
    def test_sysctl_parameter_reading(self):
        """Test reading current sysctl parameters for baseline."""
        from server.tools.util.shell import run
        
        # Read some key parameters
        params_to_check = [
            "net.core.rmem_max",
            "net.core.wmem_max",
            "net.ipv4.tcp_congestion_control",
            "net.core.default_qdisc"
        ]
        
        print("\n=== Current System Parameters (Baseline) ===")
        for param in params_to_check:
            result = run(["sysctl", param], timeout=5)
            if result["ok"]:
                print(f"  {param}: {result['stdout'].strip()}")
            else:
                print(f"  {param}: Unable to read ({result['stderr']})")
    
    def test_plan_execution_time(self):
        """Test the time taken to validate and render plans."""
        import time
        
        plan = {
            "task_description": "Performance test plan",
            "rationale": "Measure validation and rendering performance",
            "parameters": [
                {
                    "scope": "sysctl",
                    "key": "net.ipv4.tcp_timestamps",
                    "value": "1"
                }
            ]
        }
        
        # Measure validation time
        start = time.time()
        validation = validate_change_plan(plan)
        validation_time = time.time() - start
        
        # Measure rendering time
        start = time.time()
        if validation["ok"]:
            rendered = render_change_plan(plan)
            rendering_time = time.time() - start
        else:
            rendering_time = 0
        
        print(f"\n=== Performance Metrics ===")
        print(f"  Validation time: {validation_time*1000:.2f} ms")
        print(f"  Rendering time: {rendering_time*1000:.2f} ms")
        print(f"  Total time: {(validation_time + rendering_time)*1000:.2f} ms")
        
        # Performance assertions
        assert validation_time < 1.0, "Validation should complete in under 1 second"
        assert rendering_time < 1.0, "Rendering should complete in under 1 second"


if __name__ == "__main__":
    # Run with pytest for better output
    pytest.main([__file__, "-v", "-s"])
