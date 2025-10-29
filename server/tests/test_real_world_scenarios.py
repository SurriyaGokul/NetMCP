"""
Real-world scenario tests for MCP Network Optimizer.
Tests various practical use cases to ensure the system fulfills its purpose.
"""
import pytest
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from server.tools.planner import render_change_plan
from server.tools.validator import validate_change_plan


class TestRealWorldScenarios:
    """Test real-world network optimization scenarios."""
    
    def test_scenario_1_web_server_optimization(self):
        """
        Scenario: Optimize a web server for handling many concurrent connections.
        
        Expected outcome:
        - Increase socket buffers
        - Enable TCP window scaling
        - Increase SYN backlog
        - Enable SYN cookies for DDoS protection
        """
        print("\n" + "="*70)
        print("SCENARIO 1: Web Server Optimization for High Concurrent Connections")
        print("="*70)
        
        plan = {
            "task_description": "Optimize web server for 10,000+ concurrent connections",
            "rationale": "Increase connection handling capacity and buffer sizes for high traffic",
            "parameters": [
                {
                    "scope": "sysctl",
                    "key": "net.core.rmem_max",
                    "value": "16777216"
                },
                {
                    "scope": "sysctl",
                    "key": "net.core.wmem_max",
                    "value": "16777216"
                },
                {
                    "scope": "sysctl",
                    "key": "net.ipv4.tcp_max_syn_backlog",
                    "value": "4096"
                },
                {
                    "scope": "sysctl",
                    "key": "net.ipv4.tcp_syncookies",
                    "value": "1"
                },
                {
                    "scope": "sysctl",
                    "key": "net.ipv4.tcp_window_scaling",
                    "value": "1"
                }
            ]
        }
        
        self._execute_and_verify_scenario(plan)
    
    def test_scenario_2_database_server_latency(self):
        """
        Scenario: Optimize database server for low-latency queries.
        
        Expected outcome:
        - Enable TCP fast open
        - Reduce FIN timeout
        - Enable low latency mode
        - Optimize TCP memory
        """
        print("\n" + "="*70)
        print("SCENARIO 2: Database Server Optimization for Low Latency")
        print("="*70)
        
        plan = {
            "task_description": "Optimize database server for low-latency queries",
            "rationale": "Reduce connection overhead and packet processing time",
            "parameters": [
                {
                    "scope": "sysctl",
                    "key": "net.ipv4.tcp_fastopen",
                    "value": "3"
                },
                {
                    "scope": "sysctl",
                    "key": "net.ipv4.tcp_fin_timeout",
                    "value": "15"
                },
                {
                    "scope": "sysctl",
                    "key": "net.ipv4.tcp_low_latency",
                    "value": "1"
                },
                {
                    "scope": "sysctl",
                    "key": "net.ipv4.tcp_rmem",
                    "value": "4096 87380 16777216"
                },
                {
                    "scope": "sysctl",
                    "key": "net.ipv4.tcp_wmem",
                    "value": "4096 65536 16777216"
                }
            ]
        }
        
        self._execute_and_verify_scenario(plan)
    
    def test_scenario_3_video_streaming_server(self):
        """
        Scenario: Optimize server for video streaming with high throughput.
        
        Expected outcome:
        - Use BBR congestion control
        - Large send/receive buffers
        - Enable TCP timestamps
        - Use fq qdisc for better pacing
        """
        print("\n" + "="*70)
        print("SCENARIO 3: Video Streaming Server Optimization")
        print("="*70)
        
        plan = {
            "task_description": "Optimize server for high-throughput video streaming",
            "rationale": "Maximize bandwidth utilization and smooth video delivery",
            "parameters": [
                {
                    "scope": "sysctl",
                    "key": "net.ipv4.tcp_congestion_control",
                    "value": "bbr"
                },
                {
                    "scope": "sysctl",
                    "key": "net.core.default_qdisc",
                    "value": "fq"
                },
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
                    "key": "net.ipv4.tcp_timestamps",
                    "value": "1"
                }
            ]
        }
        
        self._execute_and_verify_scenario(plan)
    
    def test_scenario_4_vpn_gateway(self):
        """
        Scenario: Configure VPN gateway with packet forwarding and NAT.
        
        Expected outcome:
        - Enable IP forwarding
        - Set up NAT rules
        - Optimize connection tracking
        """
        print("\n" + "="*70)
        print("SCENARIO 4: VPN Gateway Configuration")
        print("="*70)
        
        plan = {
            "task_description": "Configure system as VPN gateway with NAT",
            "rationale": "Enable packet forwarding between VPN and LAN with connection tracking",
            "parameters": [
                {
                    "scope": "sysctl",
                    "key": "net.ipv4.ip_forward",
                    "value": "1"
                },
                {
                    "scope": "nft",
                    "table": "nat",
                    "chain": "postrouting",
                    "rule_spec": "oifname eth0 masquerade"
                }
            ]
        }
        
        self._execute_and_verify_scenario(plan)
    
    def test_scenario_5_qos_bandwidth_limiting(self):
        """
        Scenario: Set up QoS with bandwidth limiting for different traffic classes.
        
        Expected outcome:
        - Configure HTB qdisc
        - Set rate limits
        - Establish priority classes
        """
        print("\n" + "="*70)
        print("SCENARIO 5: QoS Bandwidth Limiting Configuration")
        print("="*70)
        
        plan = {
            "task_description": "Set up QoS with bandwidth limiting for office network",
            "rationale": "Prioritize business traffic and limit non-essential bandwidth usage",
            "parameters": [
                {
                    "scope": "tc",
                    "iface": "eth0",
                    "qdisc_type": "htb",
                    "handle": "1:",
                    "htb_rate": "100mbit",
                    "htb_ceil": "100mbit"
                },
                {
                    "scope": "tc",
                    "iface": "eth0",
                    "parent": "1:",
                    "classid": "1:10",
                    "htb_rate": "50mbit",
                    "htb_ceil": "80mbit",
                    "htb_priority": "1"
                },
                {
                    "scope": "tc",
                    "iface": "eth0",
                    "parent": "1:",
                    "classid": "1:20",
                    "htb_rate": "30mbit",
                    "htb_ceil": "50mbit",
                    "htb_priority": "2"
                }
            ]
        }
        
        self._execute_and_verify_scenario(plan)
    
    def test_scenario_6_gaming_router(self):
        """
        Scenario: Optimize home router for online gaming (low latency, minimal jitter).
        
        Expected outcome:
        - Enable low latency settings
        - Use fq_codel for bufferbloat reduction
        - Enable TCP fast open
        - Optimize network processing budget
        """
        print("\n" + "="*70)
        print("SCENARIO 6: Gaming Router Optimization")
        print("="*70)
        
        plan = {
            "task_description": "Optimize home router for competitive online gaming",
            "rationale": "Minimize latency and jitter for real-time game traffic",
            "parameters": [
                {
                    "scope": "sysctl",
                    "key": "net.ipv4.tcp_low_latency",
                    "value": "1"
                },
                {
                    "scope": "sysctl",
                    "key": "net.core.default_qdisc",
                    "value": "fq_codel"
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
                },
                {
                    "scope": "sysctl",
                    "key": "net.ipv4.tcp_fin_timeout",
                    "value": "10"
                }
            ]
        }
        
        self._execute_and_verify_scenario(plan)
    
    def test_scenario_7_ddos_mitigation(self):
        """
        Scenario: Configure system to handle DDoS attacks.
        
        Expected outcome:
        - Enable SYN cookies
        - Increase SYN backlog
        - Configure connection rate limiting
        - Enable connection tracking
        """
        print("\n" + "="*70)
        print("SCENARIO 7: DDoS Mitigation Configuration")
        print("="*70)
        
        plan = {
            "task_description": "Configure DDoS mitigation for public-facing web server",
            "rationale": "Protect against SYN floods and connection exhaustion attacks",
            "parameters": [
                {
                    "scope": "sysctl",
                    "key": "net.ipv4.tcp_syncookies",
                    "value": "1"
                },
                {
                    "scope": "sysctl",
                    "key": "net.ipv4.tcp_max_syn_backlog",
                    "value": "8192"
                },
                {
                    "scope": "nft",
                    "table": "filter",
                    "chain": "input",
                    "rule_spec": "tcp dport 80 limit rate 100/second accept"
                },
                {
                    "scope": "nft",
                    "table": "filter",
                    "chain": "input",
                    "rule_spec": "tcp dport 443 limit rate 100/second accept"
                }
            ]
        }
        
        self._execute_and_verify_scenario(plan)
    
    def _execute_and_verify_scenario(self, plan: dict):
        """Helper method to execute and verify a scenario."""
        print(f"\nTask: {plan['task_description']}")
        print(f"Rationale: {plan['rationale']}")
        print(f"Parameters: {len(plan['parameters'])} setting(s)\n")
        
        # Step 1: Validate
        print("Step 1: Validating plan...")
        validation = validate_change_plan(plan)
        
        if not validation["ok"]:
            print(f"  ✗ VALIDATION FAILED")
            print(f"  Issues:")
            for issue in validation.get("issues", []):
                print(f"    - {issue}")
            pytest.fail(f"Validation failed for scenario: {plan['task_description']}")
            return
        
        print(f"  ✓ Validation PASSED")
        
        # Step 2: Render
        print("\nStep 2: Rendering plan to executable commands...")
        rendered = render_change_plan(plan)
        
        print(f"  ✓ Rendering completed")
        print(f"  Generated commands: {len(rendered.get('commands', []))}")
        print(f"  Generated scripts: {len(rendered.get('scripts', []))}")
        
        # Display sample commands
        if rendered.get("commands"):
            print(f"\n  Sample commands:")
            for i, cmd in enumerate(rendered["commands"][:5], 1):
                print(f"    {i}. {cmd}")
            if len(rendered["commands"]) > 5:
                print(f"    ... and {len(rendered['commands']) - 5} more")
        
        # Display scripts
        if rendered.get("scripts"):
            print(f"\n  Scripts generated:")
            for i, script in enumerate(rendered["scripts"][:2], 1):
                print(f"    Script {i}:")
                print(f"      Interpreter: {script.get('interpreter', 'N/A')}")
                print(f"      Content preview: {script.get('content', '')[:100]}...")
        
        # Step 3: Verify structure
        print("\nStep 3: Verifying output structure...")
        assert "task_description" in rendered, "Missing task_description"
        assert "rationale" in rendered, "Missing rationale"
        assert "commands" in rendered or "scripts" in rendered, "Missing commands or scripts"
        
        print(f"  ✓ Output structure verified")
        print(f"\n{'='*70}")
        print(f"SCENARIO COMPLETED SUCCESSFULLY")
        print(f"{'='*70}\n")


class TestScenarioComparison:
    """Compare different scenarios to ensure proper differentiation."""
    
    def test_latency_vs_throughput_optimization(self):
        """Verify that latency and throughput optimizations are different."""
        print("\n" + "="*70)
        print("COMPARISON: Latency vs Throughput Optimization")
        print("="*70)
        
        latency_plan = {
            "task_description": "Low latency optimization",
            "rationale": "Minimize packet processing time",
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
                }
            ]
        }
        
        throughput_plan = {
            "task_description": "High throughput optimization",
            "rationale": "Maximize bandwidth utilization",
            "parameters": [
                {
                    "scope": "sysctl",
                    "key": "net.core.rmem_max",
                    "value": "134217728"
                },
                {
                    "scope": "sysctl",
                    "key": "net.ipv4.tcp_congestion_control",
                    "value": "bbr"
                }
            ]
        }
        
        latency_rendered = render_change_plan(latency_plan)
        throughput_rendered = render_change_plan(throughput_plan)
        
        print("\nLatency optimization commands:")
        for cmd in latency_rendered.get("commands", []):
            print(f"  - {cmd}")
        
        print("\nThroughput optimization commands:")
        for cmd in throughput_rendered.get("commands", []):
            print(f"  - {cmd}")
        
        # Verify they generate different commands
        latency_cmds = set(latency_rendered.get("commands", []))
        throughput_cmds = set(throughput_rendered.get("commands", []))
        
        assert latency_cmds != throughput_cmds, "Latency and throughput optimizations should be different"
        print("\n✓ Confirmed: Different optimization strategies generate different configurations")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
