"""
Unit tests for validator.py
Tests validation of parameter plans including:
- Out-of-range DSCP values
- Over-bandwidth limits
- Unknown keys in various parts of the plan
"""

import sys
import os
import unittest

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools.validator import validate_change_plan


class TestValidator(unittest.TestCase):
    """Test cases for the validate_change_plan function"""
    
    def setUp(self):
        """Set up valid base plan for testing"""
        self.valid_plan = {
            "iface": "eth0",
            "profile": "gaming",
            "changes": {
                "qdisc": {
                    "type": "fq_codel",
                    "params": {"limit": 1000}
                },
                "shaper": {
                    "egress_mbit": 1000,
                    "ingress_mbit": 500
                }
            }
        }
    
    # Tests for DSCP validation
    def test_valid_dscp_values(self):
        """Test that valid DSCP values are accepted"""
        valid_dscp_values = ["EF", "CS6", "CS5", "CS4", "AF41", "AF42", "AF43"]
        
        for dscp in valid_dscp_values:
            with self.subTest(dscp=dscp):
                plan = {
                    "iface": "eth0",
                    "profile": "gaming",
                    "changes": {
                        "dscp": [
                            {
                                "match": {"proto": "tcp", "dports": [443]},
                                "dscp": dscp
                            }
                        ]
                    }
                }
                result = validate_change_plan(plan)
                self.assertTrue(result["ok"], f"Valid DSCP {dscp} was rejected: {result.get('errors')}")
    
    def test_invalid_dscp_value(self):
        """Test that invalid DSCP values are rejected"""
        # Invalid DSCP value (not in allowed list)
        plan = {
            "iface": "eth0",
            "profile": "gaming",
            "changes": {
                "dscp": [
                    {
                        "match": {"proto": "tcp", "dports": [443]},
                        "dscp": "INVALID"
                    }
                ]
            }
        }
        result = validate_change_plan(plan)
        self.assertFalse(result["ok"])
        self.assertTrue(any("INVALID" in err or "dscp" in err.lower() for err in result["errors"]))
    
    def test_out_of_range_dscp_numeric(self):
        """Test that numeric DSCP values outside the valid range are rejected"""
        # DSCP values must be strings from the allowed set, not numbers
        plan = {
            "iface": "eth0",
            "profile": "gaming",
            "changes": {
                "dscp": [
                    {
                        "match": {"proto": "tcp", "dports": [443]},
                        "dscp": "99"  # Invalid - not in allowed set
                    }
                ]
            }
        }
        result = validate_change_plan(plan)
        self.assertFalse(result["ok"])
        # Should fail schema validation since "99" is not in the Literal type
        self.assertTrue(len(result["errors"]) > 0)
    
    # Tests for bandwidth validation
    def test_valid_bandwidth_values(self):
        """Test that valid bandwidth values are accepted"""
        plan = {
            "iface": "eth0",
            "profile": "gaming",
            "changes": {
                "shaper": {
                    "egress_mbit": 1000,
                    "ingress_mbit": 500,
                    "ceil_mbit": 1500
                }
            }
        }
        result = validate_change_plan(plan)
        self.assertTrue(result["ok"], f"Valid bandwidth was rejected: {result.get('errors')}")
    
    def test_over_bandwidth_egress(self):
        """Test that egress bandwidth over 100Gbps is rejected"""
        plan = {
            "iface": "eth0",
            "profile": "gaming",
            "changes": {
                "shaper": {
                    "egress_mbit": 100001  # Over 100Gbps
                }
            }
        }
        result = validate_change_plan(plan)
        self.assertFalse(result["ok"])
        self.assertTrue(any("egress_mbit" in err and "100000" in err for err in result["errors"]))
    
    def test_over_bandwidth_ingress(self):
        """Test that ingress bandwidth over 100Gbps is rejected"""
        plan = {
            "iface": "eth0",
            "profile": "gaming",
            "changes": {
                "shaper": {
                    "ingress_mbit": 150000  # Over 100Gbps
                }
            }
        }
        result = validate_change_plan(plan)
        self.assertFalse(result["ok"])
        self.assertTrue(any("ingress_mbit" in err and "100000" in err for err in result["errors"]))
    
    def test_over_bandwidth_ceil(self):
        """Test that ceil bandwidth over 100Gbps is rejected"""
        plan = {
            "iface": "eth0",
            "profile": "gaming",
            "changes": {
                "shaper": {
                    "egress_mbit": 1000,
                    "ceil_mbit": 200000  # Over 100Gbps
                }
            }
        }
        result = validate_change_plan(plan)
        self.assertFalse(result["ok"])
        self.assertTrue(any("ceil_mbit" in err and "100000" in err for err in result["errors"]))
    
    def test_ceil_less_than_egress(self):
        """Test that ceil must be >= egress"""
        plan = {
            "iface": "eth0",
            "profile": "gaming",
            "changes": {
                "shaper": {
                    "egress_mbit": 1000,
                    "ceil_mbit": 500  # Less than egress
                }
            }
        }
        result = validate_change_plan(plan)
        self.assertFalse(result["ok"])
        self.assertTrue(any("ceil" in err and "egress" in err for err in result["errors"]))
    
    def test_zero_bandwidth(self):
        """Test that zero bandwidth is rejected"""
        plan = {
            "iface": "eth0",
            "profile": "gaming",
            "changes": {
                "shaper": {
                    "egress_mbit": 0  # Zero is invalid
                }
            }
        }
        result = validate_change_plan(plan)
        self.assertFalse(result["ok"])
    
    def test_negative_bandwidth(self):
        """Test that negative bandwidth is rejected"""
        plan = {
            "iface": "eth0",
            "profile": "gaming",
            "changes": {
                "shaper": {
                    "egress_mbit": -100  # Negative is invalid
                }
            }
        }
        result = validate_change_plan(plan)
        self.assertFalse(result["ok"])
    
    # Tests for unknown keys
    def test_unknown_top_level_keys(self):
        """Test that unknown keys at the top level are rejected"""
        plan = {
            "iface": "eth0",
            "profile": "gaming",
            "changes": {},
            "unknown_key": "invalid",  # Unknown key
            "another_bad_key": 123
        }
        result = validate_change_plan(plan)
        self.assertFalse(result["ok"])
        self.assertTrue(any("unknown" in err.lower() for err in result["errors"]))
        self.assertTrue(any("unknown_key" in err for err in result["errors"]))
    
    def test_unknown_keys_in_changes(self):
        """Test that unknown keys in changes are rejected"""
        plan = {
            "iface": "eth0",
            "profile": "gaming",
            "changes": {
                "qdisc": {"type": "fq_codel", "params": {}},
                "invalid_change": "bad",  # Unknown key
                "another_unknown": 123
            }
        }
        result = validate_change_plan(plan)
        self.assertFalse(result["ok"])
        self.assertTrue(any("unknown" in err.lower() and "changes" in err.lower() for err in result["errors"]))
    
    def test_unknown_keys_in_qdisc(self):
        """Test that unknown keys in qdisc are rejected"""
        plan = {
            "iface": "eth0",
            "profile": "gaming",
            "changes": {
                "qdisc": {
                    "type": "fq_codel",
                    "params": {},
                    "unknown_qdisc_field": "bad"  # Unknown key
                }
            }
        }
        result = validate_change_plan(plan)
        self.assertFalse(result["ok"])
        self.assertTrue(any("unknown" in err.lower() and "qdisc" in err.lower() for err in result["errors"]))
    
    def test_unknown_keys_in_offloads(self):
        """Test that unknown keys in offloads are rejected"""
        plan = {
            "iface": "eth0",
            "profile": "gaming",
            "changes": {
                "offloads": {
                    "gro": True,
                    "gso": False,
                    "invalid_offload": True  # Unknown key
                }
            }
        }
        result = validate_change_plan(plan)
        self.assertFalse(result["ok"])
        self.assertTrue(any("unknown" in err.lower() and "offloads" in err.lower() for err in result["errors"]))
    
    def test_multiple_errors(self):
        """Test that multiple validation errors are all reported"""
        plan = {
            "iface": "eth0",
            "profile": "gaming",
            "changes": {
                "shaper": {
                    "egress_mbit": 200000,  # Over limit
                    "ceil_mbit": 100  # Less than egress (if egress were valid)
                },
                "invalid_key": "bad"  # Unknown key
            },
            "bad_top_level": "also bad"  # Unknown top-level key
        }
        result = validate_change_plan(plan)
        self.assertFalse(result["ok"])
        # Should report multiple errors
        self.assertGreater(len(result["errors"]), 1)
    
    # Tests for valid edge cases
    def test_minimal_valid_plan(self):
        """Test a minimal valid plan"""
        plan = {
            "iface": "eth0",
            "profile": "gaming",
            "changes": {}
        }
        result = validate_change_plan(plan)
        self.assertTrue(result["ok"], f"Minimal valid plan was rejected: {result.get('errors')}")
    
    def test_valid_plan_with_all_fields(self):
        """Test a complete valid plan with all optional fields"""
        plan = {
            "iface": "eth0",
            "profile": "gaming",
            "changes": {
                "qdisc": {
                    "type": "fq_codel",
                    "params": {"limit": 1000, "target": "5ms"}
                },
                "shaper": {
                    "egress_mbit": 1000,
                    "ingress_mbit": 500,
                    "ceil_mbit": 1500
                },
                "sysctl": {
                    "net.ipv4.tcp_congestion_control": "bbr"
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
                    }
                ],
                "mtu": 1500
            },
            "validate": {
                "targets": {"ping": "8.8.8.8"},
                "objectives": {"latency_p95_ms": 20}
            },
            "rationale": ["Low latency required", "BBR for throughput"]
        }
        result = validate_change_plan(plan)
        self.assertTrue(result["ok"], f"Complete valid plan was rejected: {result.get('errors')}")
    
    def test_invalid_input_type(self):
        """Test that non-dict input is rejected"""
        result = validate_change_plan("not a dict")
        self.assertFalse(result["ok"])
        self.assertTrue(any("dict" in err.lower() for err in result["errors"]))
    
    def test_missing_required_fields(self):
        """Test that missing required fields are rejected"""
        plan = {
            "iface": "eth0",
            # Missing "profile" - required field
            "changes": {}
        }
        result = validate_change_plan(plan)
        self.assertFalse(result["ok"])
    
    def test_invalid_qdisc_type(self):
        """Test that invalid qdisc type is rejected"""
        plan = {
            "iface": "eth0",
            "profile": "gaming",
            "changes": {
                "qdisc": {
                    "type": "invalid_qdisc",  # Not in allowed types
                    "params": {}
                }
            }
        }
        result = validate_change_plan(plan)
        self.assertFalse(result["ok"])
    
    def test_valid_qdisc_types(self):
        """Test that all valid qdisc types are accepted"""
        valid_types = ["cake", "fq_codel", "htb"]
        
        for qdisc_type in valid_types:
            with self.subTest(qdisc_type=qdisc_type):
                plan = {
                    "iface": "eth0",
                    "profile": "gaming",
                    "changes": {
                        "qdisc": {
                            "type": qdisc_type,
                            "params": {}
                        }
                    }
                }
                result = validate_change_plan(plan)
                self.assertTrue(result["ok"], f"Valid qdisc type {qdisc_type} was rejected: {result.get('errors')}")


if __name__ == "__main__":
    unittest.main()
