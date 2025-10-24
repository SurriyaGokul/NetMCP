"""
Unit tests for planner.py
Tests that the planner produces stable and deterministic outputs:
- Same input always produces same output
- Order of operations is consistent
- Command generation is deterministic
"""

import sys
import os
import unittest
import hashlib
import json

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools.planner import render_change_plan


class TestPlanner(unittest.TestCase):
    """Test cases for the render_change_plan function"""
    
    def setUp(self):
        """Set up test plans"""
        self.basic_plan = {
            "iface": "eth0",
            "profile": "gaming",
            "changes": {
                "sysctl": {
                    "net.ipv4.tcp_congestion_control": "bbr",
                    "net.core.default_qdisc": "fq"
                }
            }
        }
        
        self.complex_plan = {
            "iface": "eth0",
            "profile": "gaming",
            "changes": {
                "qdisc": {
                    "type": "htb",
                    "params": {}
                },
                "shaper": {
                    "egress_mbit": 1000,
                    "ceil_mbit": 1500
                },
                "sysctl": {
                    "net.ipv4.tcp_congestion_control": "bbr",
                    "net.core.default_qdisc": "fq",
                    "net.ipv4.tcp_window_scaling": "1"
                },
                "offloads": {
                    "gro": True,
                    "gso": False,
                    "tso": True,
                    "lro": False
                },
                "dscp": [
                    {
                        "match": {"proto": "tcp", "dports": [443]},
                        "dscp": "EF"
                    },
                    {
                        "match": {"proto": "udp", "dports": [53]},
                        "dscp": "CS5"
                    }
                ],
                "mtu": 1500
            }
        }
    
    # Tests for determinism
    def test_deterministic_output_basic(self):
        """Test that the same basic plan produces identical output multiple times"""
        outputs = []
        for _ in range(5):
            result = render_change_plan(self.basic_plan)
            outputs.append(result)
        
        # All outputs should be identical
        for i in range(1, len(outputs)):
            self.assertEqual(outputs[0], outputs[i], 
                           f"Output {i} differs from first output")
    
    def test_deterministic_output_complex(self):
        """Test that the same complex plan produces identical output multiple times"""
        outputs = []
        for _ in range(5):
            result = render_change_plan(self.complex_plan)
            outputs.append(result)
        
        # All outputs should be identical
        for i in range(1, len(outputs)):
            self.assertEqual(outputs[0], outputs[i], 
                           f"Output {i} differs from first output")
    
    def test_deterministic_hash_basic(self):
        """Test that output hash is consistent for basic plan"""
        hashes = []
        for _ in range(5):
            result = render_change_plan(self.basic_plan)
            result_str = json.dumps(result, sort_keys=True)
            hash_val = hashlib.sha256(result_str.encode()).hexdigest()
            hashes.append(hash_val)
        
        # All hashes should be identical
        self.assertEqual(len(set(hashes)), 1, 
                        f"Got different hashes: {set(hashes)}")
    
    def test_deterministic_hash_complex(self):
        """Test that output hash is consistent for complex plan"""
        hashes = []
        for _ in range(5):
            result = render_change_plan(self.complex_plan)
            result_str = json.dumps(result, sort_keys=True)
            hash_val = hashlib.sha256(result_str.encode()).hexdigest()
            hashes.append(hash_val)
        
        # All hashes should be identical
        self.assertEqual(len(set(hashes)), 1, 
                        f"Got different hashes: {set(hashes)}")
    
    # Tests for stable ordering
    def test_sysctl_command_order(self):
        """Test that sysctl commands maintain consistent order"""
        plan = {
            "iface": "eth0",
            "profile": "gaming",
            "changes": {
                "sysctl": {
                    "net.ipv4.tcp_congestion_control": "bbr",
                    "net.core.default_qdisc": "fq",
                    "net.ipv4.tcp_window_scaling": "1",
                    "net.ipv4.tcp_timestamps": "1"
                }
            }
        }
        
        # Run multiple times and check order consistency
        orders = []
        for _ in range(5):
            result = render_change_plan(plan)
            orders.append(result["sysctl_cmds"])
        
        # All orders should be identical
        for i in range(1, len(orders)):
            self.assertEqual(orders[0], orders[i], 
                           "Sysctl command order is not stable")
    
    def test_ethtool_command_order(self):
        """Test that ethtool commands maintain consistent order"""
        plan = {
            "iface": "eth0",
            "profile": "gaming",
            "changes": {
                "offloads": {
                    "gro": True,
                    "gso": False,
                    "tso": True,
                    "lro": False
                }
            }
        }
        
        # Run multiple times and check order consistency
        orders = []
        for _ in range(5):
            result = render_change_plan(plan)
            orders.append(result["ethtool_cmds"])
        
        # All orders should be identical
        for i in range(1, len(orders)):
            self.assertEqual(orders[0], orders[i], 
                           "Ethtool command order is not stable")
    
    def test_dscp_rule_order(self):
        """Test that DSCP rules maintain consistent order"""
        plan = {
            "iface": "eth0",
            "profile": "gaming",
            "changes": {
                "dscp": [
                    {"match": {"proto": "tcp", "dports": [443]}, "dscp": "EF"},
                    {"match": {"proto": "udp", "dports": [53]}, "dscp": "CS5"},
                    {"match": {"proto": "tcp", "dports": [80]}, "dscp": "CS4"}
                ]
            }
        }
        
        # Run multiple times and check script consistency
        scripts = []
        for _ in range(5):
            result = render_change_plan(plan)
            scripts.append(result["nft_script"])
        
        # All scripts should be identical
        for i in range(1, len(scripts)):
            self.assertEqual(scripts[0], scripts[i], 
                           "NFT script order is not stable")
    
    # Tests for output structure stability
    def test_output_structure_complete(self):
        """Test that output always has the same structure"""
        result = render_change_plan(self.complex_plan)
        
        # Check all expected keys are present
        expected_keys = {"sysctl_cmds", "tc_script", "nft_script", 
                        "ethtool_cmds", "ip_link_cmds"}
        self.assertEqual(set(result.keys()), expected_keys, 
                        "Output structure is not stable")
    
    def test_output_structure_empty(self):
        """Test that output structure is stable even with empty changes"""
        plan = {
            "iface": "eth0",
            "profile": "gaming",
            "changes": {}
        }
        
        result = render_change_plan(plan)
        
        # Check all expected keys are present
        expected_keys = {"sysctl_cmds", "tc_script", "nft_script", 
                        "ethtool_cmds", "ip_link_cmds"}
        self.assertEqual(set(result.keys()), expected_keys, 
                        "Output structure is not stable for empty changes")
        
        # Check empty fields are properly initialized
        self.assertEqual(result["sysctl_cmds"], [])
        self.assertEqual(result["tc_script"], "")
        self.assertEqual(result["nft_script"], "")
        self.assertEqual(result["ethtool_cmds"], [])
        self.assertEqual(result["ip_link_cmds"], [])
    
    # Tests for specific renderings
    def test_sysctl_rendering_format(self):
        """Test that sysctl commands are rendered in consistent format"""
        plan = {
            "iface": "eth0",
            "profile": "gaming",
            "changes": {
                "sysctl": {
                    "net.ipv4.tcp_congestion_control": "bbr"
                }
            }
        }
        
        result = render_change_plan(plan)
        
        # Check command format
        self.assertEqual(len(result["sysctl_cmds"]), 1)
        self.assertEqual(result["sysctl_cmds"][0], 
                        "sysctl -w net.ipv4.tcp_congestion_control=bbr")
    
    def test_tc_script_format_stability(self):
        """Test that TC script format is stable"""
        plan = {
            "iface": "eth0",
            "profile": "gaming",
            "changes": {
                "qdisc": {
                    "type": "fq_codel",
                    "params": {}
                }
            }
        }
        
        # Run multiple times
        scripts = []
        for _ in range(5):
            result = render_change_plan(plan)
            scripts.append(result["tc_script"])
        
        # All should be identical
        for i in range(1, len(scripts)):
            self.assertEqual(scripts[0], scripts[i])
        
        # Check script contains expected elements
        self.assertIn("tc qdisc", scripts[0])
        self.assertIn("eth0", scripts[0])
    
    def test_mtu_rendering_stability(self):
        """Test that MTU commands are rendered consistently"""
        plan = {
            "iface": "eth0",
            "profile": "gaming",
            "changes": {
                "mtu": 1500
            }
        }
        
        # Run multiple times
        commands = []
        for _ in range(5):
            result = render_change_plan(plan)
            commands.append(result["ip_link_cmds"])
        
        # All should be identical
        for i in range(1, len(commands)):
            self.assertEqual(commands[0], commands[i])
        
        # Check format
        self.assertEqual(commands[0], ["ip link set dev eth0 mtu 1500"])
    
    # Tests for different interface names
    def test_interface_name_consistency(self):
        """Test that different interface names don't affect determinism"""
        interfaces = ["eth0", "eth1", "enp0s3", "wlan0"]
        
        for iface in interfaces:
            with self.subTest(interface=iface):
                plan = {
                    "iface": iface,
                    "profile": "gaming",
                    "changes": {
                        "mtu": 1500
                    }
                }
                
                # Run multiple times for each interface
                results = []
                for _ in range(3):
                    result = render_change_plan(plan)
                    results.append(result)
                
                # All results for same interface should be identical
                for i in range(1, len(results)):
                    self.assertEqual(results[0], results[i])
    
    # Tests for qdisc types
    def test_qdisc_type_determinism(self):
        """Test that different qdisc types produce deterministic output"""
        qdisc_types = ["cake", "fq_codel", "htb"]
        
        for qtype in qdisc_types:
            with self.subTest(qdisc_type=qtype):
                plan = {
                    "iface": "eth0",
                    "profile": "gaming",
                    "changes": {
                        "qdisc": {
                            "type": qtype,
                            "params": {}
                        }
                    }
                }
                
                # Run multiple times
                results = []
                for _ in range(5):
                    result = render_change_plan(plan)
                    results.append(result)
                
                # All should be identical
                for i in range(1, len(results)):
                    self.assertEqual(results[0], results[i], 
                                   f"Qdisc type {qtype} produces non-deterministic output")
    
    # Tests for edge cases
    def test_empty_params_stability(self):
        """Test that empty params dict doesn't affect stability"""
        plan = {
            "iface": "eth0",
            "profile": "gaming",
            "changes": {
                "qdisc": {
                    "type": "fq_codel",
                    "params": {}
                }
            }
        }
        
        results = []
        for _ in range(5):
            result = render_change_plan(plan)
            results.append(result)
        
        for i in range(1, len(results)):
            self.assertEqual(results[0], results[i])
    
    def test_null_optional_fields_stability(self):
        """Test that null optional fields don't affect stability"""
        plan = {
            "iface": "eth0",
            "profile": "gaming",
            "changes": {
                "shaper": {
                    "egress_mbit": 1000
                    # ingress_mbit and ceil_mbit are None/omitted
                }
            }
        }
        
        results = []
        for _ in range(5):
            result = render_change_plan(plan)
            results.append(result)
        
        for i in range(1, len(results)):
            self.assertEqual(results[0], results[i])
    
    # Test that different plans produce different outputs
    def test_different_plans_produce_different_outputs(self):
        """Test that different input plans produce different outputs"""
        plan1 = {
            "iface": "eth0",
            "profile": "gaming",
            "changes": {
                "mtu": 1500
            }
        }
        
        plan2 = {
            "iface": "eth0",
            "profile": "gaming",
            "changes": {
                "mtu": 9000
            }
        }
        
        result1 = render_change_plan(plan1)
        result2 = render_change_plan(plan2)
        
        self.assertNotEqual(result1, result2, 
                          "Different plans should produce different outputs")
    
    def test_full_plan_determinism(self):
        """Test full determinism with all features enabled"""
        # Run the complex plan many times
        results = []
        for _ in range(10):
            result = render_change_plan(self.complex_plan)
            results.append(result)
        
        # Calculate unique outputs
        unique_results = []
        for result in results:
            result_str = json.dumps(result, sort_keys=True)
            if result_str not in unique_results:
                unique_results.append(result_str)
        
        # Should only have one unique output
        self.assertEqual(len(unique_results), 1, 
                        f"Got {len(unique_results)} different outputs, expected 1")


if __name__ == "__main__":
    unittest.main()
