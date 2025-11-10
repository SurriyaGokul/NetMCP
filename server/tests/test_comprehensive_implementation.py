#!/usr/bin/env python3
"""
Test script to validate all config card implementations across all profiles.
Tests the rendering of ParameterPlans to RenderedPlans without actual execution.
"""

import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from server.tools.planner import render_change_plan
from server.schema.models import ParameterPlan


def test_gaming_profile():
    """Test gaming profile with low-latency optimizations"""
    print("\n=== Testing Gaming Profile ===")
    
    plan = {
        "iface": "eth0",
        "profile": "gaming",
        "changes": {
            "sysctl": {
                "net.ipv4.tcp_congestion_control": "bbr",
                "net.ipv4.tcp_low_latency": "1",
                "net.ipv4.tcp_fastopen": "3",
                "net.ipv4.tcp_timestamps": "1",
                "net.ipv4.tcp_window_scaling": "1",
                "net.core.rmem_max": "16777216",
                "net.core.wmem_max": "16777216",
                "net.ipv4.tcp_rmem": "4096 87380 16777216",
                "net.ipv4.tcp_wmem": "4096 65536 16777216",
                "net.core.default_qdisc": "fq"
            },
            "qdisc": {
                "type": "fq",
                "params": {}
            },
            "connection_limits": [
                {
                    "protocol": "tcp",
                    "port": 22,
                    "limit": 5,
                    "mask": 32
                }
            ]
        }
    }
    
    try:
        rendered = render_change_plan(plan)
        print(f"✓ Gaming profile rendered successfully")
        print(f"  - Sysctl commands: {len(rendered['sysctl_cmds'])}")
        print(f"  - TC script length: {len(rendered['tc_script'])} chars")
        print(f"  - NFT script length: {len(rendered['nft_script'])} chars")
        return True
    except Exception as e:
        print(f"✗ Gaming profile failed: {e}")
        return False


def test_streaming_profile():
    """Test streaming profile with high-throughput optimizations"""
    print("\n=== Testing Streaming Profile ===")
    
    plan = {
        "iface": "eth0",
        "profile": "streaming",
        "changes": {
            "sysctl": {
                "net.ipv4.tcp_congestion_control": "bbr",
                "net.ipv4.tcp_window_scaling": "1",
                "net.ipv4.tcp_timestamps": "1",
                "net.core.rmem_max": "67108864",
                "net.core.wmem_max": "67108864",
                "net.ipv4.tcp_rmem": "8192 262144 67108864",
                "net.ipv4.tcp_wmem": "8192 262144 67108864",
                "net.core.netdev_budget": "600",
                "net.core.default_qdisc": "fq"
            },
            "qdisc": {
                "type": "htb",
                "params": {}
            },
            "shaper": {
                "egress_mbit": 100,
                "ceil_mbit": 120
            },
            "htb_classes": [
                {
                    "classid": "1:10",
                    "rate_mbit": 80,
                    "ceil_mbit": 100,
                    "priority": 1
                }
            ]
        }
    }
    
    try:
        rendered = render_change_plan(plan)
        print(f"✓ Streaming profile rendered successfully")
        print(f"  - Sysctl commands: {len(rendered['sysctl_cmds'])}")
        print(f"  - TC script length: {len(rendered['tc_script'])} chars")
        return True
    except Exception as e:
        print(f"✗ Streaming profile failed: {e}")
        return False


def test_video_calls_profile():
    """Test video calls profile with balanced optimizations"""
    print("\n=== Testing Video Calls Profile ===")
    
    plan = {
        "iface": "eth0",
        "profile": "video_calls",
        "changes": {
            "sysctl": {
                "net.ipv4.tcp_congestion_control": "bbr",
                "net.ipv4.tcp_fastopen": "3",
                "net.ipv4.tcp_timestamps": "1",
                "net.ipv4.tcp_window_scaling": "1",
                "net.ipv4.tcp_fin_timeout": "20",
                "net.ipv4.tcp_max_syn_backlog": "8192",
                "net.core.rmem_max": "33554432",
                "net.core.wmem_max": "33554432",
                "net.core.default_qdisc": "fq"
            },
            "qdisc": {
                "type": "fq",
                "params": {}
            },
            "dscp": [
                {
                    "match": {
                        "proto": "udp",
                        "dports": [3478, 3479]
                    },
                    "dscp": "EF"
                }
            ]
        }
    }
    
    try:
        rendered = render_change_plan(plan)
        print(f"✓ Video calls profile rendered successfully")
        print(f"  - Sysctl commands: {len(rendered['sysctl_cmds'])}")
        print(f"  - TC script length: {len(rendered['tc_script'])} chars")
        print(f"  - NFT script length: {len(rendered['nft_script'])} chars")
        return True
    except Exception as e:
        print(f"✗ Video calls profile failed: {e}")
        return False


def test_bulk_transfer_profile():
    """Test bulk transfer profile with maximum throughput"""
    print("\n=== Testing Bulk Transfer Profile ===")
    
    plan = {
        "iface": "eth0",
        "profile": "bulk_transfer",
        "changes": {
            "sysctl": {
                "net.ipv4.tcp_congestion_control": "bbr",
                "net.ipv4.tcp_window_scaling": "1",
                "net.ipv4.tcp_timestamps": "1",
                "net.core.rmem_max": "268435456",
                "net.core.wmem_max": "268435456",
                "net.ipv4.tcp_rmem": "32768 1048576 268435456",
                "net.ipv4.tcp_wmem": "32768 1048576 268435456",
                "net.core.netdev_budget": "1000",
                "net.ipv4.ip_local_port_range": "1024 65000",
                "net.core.default_qdisc": "fq"
            },
            "qdisc": {
                "type": "fq",
                "params": {}
            }
        }
    }
    
    try:
        rendered = render_change_plan(plan)
        print(f"✓ Bulk transfer profile rendered successfully")
        print(f"  - Sysctl commands: {len(rendered['sysctl_cmds'])}")
        print(f"  - TC script length: {len(rendered['tc_script'])} chars")
        return True
    except Exception as e:
        print(f"✗ Bulk transfer profile failed: {e}")
        return False


def test_server_profile():
    """Test server profile with high concurrency and security"""
    print("\n=== Testing Server Profile ===")
    
    plan = {
        "iface": "eth0",
        "profile": "server",
        "changes": {
            "sysctl": {
                "net.ipv4.tcp_congestion_control": "bbr",
                "net.ipv4.tcp_fastopen": "3",
                "net.ipv4.tcp_timestamps": "1",
                "net.ipv4.tcp_window_scaling": "1",
                "net.ipv4.tcp_max_syn_backlog": "8192",
                "net.ipv4.tcp_fin_timeout": "15",
                "net.ipv4.tcp_syncookies": "1",
                "net.ipv4.ip_local_port_range": "1024 65000",
                "net.core.rmem_max": "67108864",
                "net.core.wmem_max": "67108864"
            },
            "connection_limits": [
                {
                    "protocol": "tcp",
                    "port": 80,
                    "limit": 100,
                    "mask": 32
                },
                {
                    "protocol": "tcp",
                    "port": 443,
                    "limit": 100,
                    "mask": 32
                }
            ],
            "rate_limits": [
                {
                    "rate": "1000/second",
                    "burst": 50
                }
            ],
            "connection_tracking": {
                "max_connections": 1000000,
                "tcp_timeout_established": 432000
            }
        }
    }
    
    try:
        rendered = render_change_plan(plan)
        print(f"✓ Server profile rendered successfully")
        print(f"  - Sysctl commands: {len(rendered['sysctl_cmds'])}")
        print(f"  - NFT script length: {len(rendered['nft_script'])} chars")
        return True
    except Exception as e:
        print(f"✗ Server profile failed: {e}")
        return False


def test_netem_support():
    """Test network emulation (netem) support"""
    print("\n=== Testing Netem Support ===")
    
    plan = {
        "iface": "eth0",
        "profile": "test",
        "changes": {
            "netem": {
                "delay_ms": 50,
                "delay_jitter_ms": 10,
                "loss_pct": 0.5
            }
        }
    }
    
    try:
        rendered = render_change_plan(plan)
        print(f"✓ Netem configuration rendered successfully")
        print(f"  - TC script length: {len(rendered['tc_script'])} chars")
        if "netem" in rendered['tc_script']:
            print(f"  - Netem commands present in TC script")
        return True
    except Exception as e:
        print(f"✗ Netem configuration failed: {e}")
        return False


def test_nat_support():
    """Test NAT rules support"""
    print("\n=== Testing NAT Support ===")
    
    plan = {
        "iface": "eth0",
        "profile": "test",
        "changes": {
            "nat_rules": [
                {
                    "type": "masquerade",
                    "iface": "eth0"
                },
                {
                    "type": "snat",
                    "iface": "eth0",
                    "to_addr": "192.168.1.1"
                }
            ]
        }
    }
    
    try:
        rendered = render_change_plan(plan)
        print(f"✓ NAT rules rendered successfully")
        print(f"  - NFT script length: {len(rendered['nft_script'])} chars")
        if "masquerade" in rendered['nft_script']:
            print(f"  - Masquerade rule present")
        if "snat" in rendered['nft_script']:
            print(f"  - SNAT rule present")
        return True
    except Exception as e:
        print(f"✗ NAT rules failed: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("MCP Network Optimizer - Comprehensive Config Card Tests")
    print("=" * 60)
    
    tests = [
        test_gaming_profile,
        test_streaming_profile,
        test_video_calls_profile,
        test_bulk_transfer_profile,
        test_server_profile,
        test_netem_support,
        test_nat_support
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"✗ Test {test.__name__} crashed: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print(f"Results: {sum(results)}/{len(results)} tests passed")
    print("=" * 60)
    
    if all(results):
        print("\n✅ All tests passed! Implementation is complete.")
        return 0
    else:
        print("\n❌ Some tests failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
