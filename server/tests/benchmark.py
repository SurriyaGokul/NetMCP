#!/usr/bin/env python3
"""
Performance benchmark script for MCP Network Optimizer.
Measures the actual impact of network optimizations on system performance.
"""
import subprocess
import time
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from server.tools.util.shell import run


class NetworkBenchmark:
    """Benchmark network performance before and after optimizations."""
    
    def __init__(self):
        self.results = {}
    
    def measure_tcp_throughput(self, host: str = "127.0.0.1", port: int = 5001) -> Dict:
        """
        Measure TCP throughput using iperf3 (if available).
        Returns throughput in Mbits/sec.
        """
        print(f"Measuring TCP throughput to {host}:{port}...")
        
        # Check if iperf3 is available
        check = run(["which", "iperf3"], timeout=2)
        if not check["ok"]:
            return {
                "available": False,
                "message": "iperf3 not installed. Install with: sudo apt-get install iperf3"
            }
        
        # Try to run a quick test (requires iperf3 server running)
        result = run(["iperf3", "-c", host, "-t", "5", "-J"], timeout=10)
        
        if result["ok"]:
            try:
                data = json.loads(result["stdout"])
                throughput = data["end"]["sum_received"]["bits_per_second"] / 1_000_000
                return {
                    "available": True,
                    "throughput_mbps": throughput,
                    "message": f"Throughput: {throughput:.2f} Mbps"
                }
            except (json.JSONDecodeError, KeyError) as e:
                return {
                    "available": True,
                    "error": str(e),
                    "message": "iperf3 test failed or server not running"
                }
        else:
            return {
                "available": True,
                "message": "iperf3 server not available or connection failed"
            }
    
    def measure_tcp_latency(self, host: str = "8.8.8.8", count: int = 10) -> Dict:
        """
        Measure TCP latency using ping.
        Returns average latency in ms.
        """
        print(f"Measuring latency to {host} ({count} packets)...")
        
        result = run(["ping", "-c", str(count), host], timeout=15)
        
        if result["ok"]:
            # Parse ping output for statistics
            output = result["stdout"]
            for line in output.split("\n"):
                if "rtt min/avg/max/mdev" in line or "min/avg/max" in line:
                    # Format: rtt min/avg/max/mdev = 10.123/15.456/20.789/2.345 ms
                    parts = line.split("=")
                    if len(parts) > 1:
                        stats = parts[1].strip().split()[0]  # Get the stats part
                        values = stats.split("/")
                        if len(values) >= 3:
                            return {
                                "available": True,
                                "min_ms": float(values[0]),
                                "avg_ms": float(values[1]),
                                "max_ms": float(values[2]),
                                "message": f"Average latency: {values[1]} ms"
                            }
            
            return {
                "available": True,
                "message": "Ping successful but could not parse statistics"
            }
        else:
            return {
                "available": False,
                "message": f"Ping failed: {result['stderr']}"
            }
    
    def measure_connection_handling(self) -> Dict:
        """
        Measure system's connection handling capacity.
        Checks current connection limits and active connections.
        """
        print("Measuring connection handling capacity...")
        
        results = {}
        
        # Check SYN backlog
        result = run(["sysctl", "net.ipv4.tcp_max_syn_backlog"], timeout=2)
        if result["ok"]:
            value = result["stdout"].split("=")[1].strip()
            results["tcp_max_syn_backlog"] = int(value)
        
        # Check SYN cookies status
        result = run(["sysctl", "net.ipv4.tcp_syncookies"], timeout=2)
        if result["ok"]:
            value = result["stdout"].split("=")[1].strip()
            results["tcp_syncookies_enabled"] = value == "1"
        
        # Check max connections
        result = run(["sysctl", "net.core.somaxconn"], timeout=2)
        if result["ok"]:
            value = result["stdout"].split("=")[1].strip()
            results["somaxconn"] = int(value)
        
        results["available"] = True
        results["message"] = f"SYN backlog: {results.get('tcp_max_syn_backlog', 'N/A')}, somaxconn: {results.get('somaxconn', 'N/A')}"
        
        return results
    
    def measure_buffer_sizes(self) -> Dict:
        """
        Measure current network buffer sizes.
        """
        print("Measuring network buffer sizes...")
        
        results = {}
        
        params = [
            "net.core.rmem_max",
            "net.core.wmem_max",
            "net.core.rmem_default",
            "net.core.wmem_default"
        ]
        
        for param in params:
            result = run(["sysctl", param], timeout=2)
            if result["ok"]:
                value = result["stdout"].split("=")[1].strip()
                results[param] = int(value)
        
        results["available"] = True
        results["message"] = f"rmem_max: {results.get('net.core.rmem_max', 0) / 1024 / 1024:.1f} MB, wmem_max: {results.get('net.core.wmem_max', 0) / 1024 / 1024:.1f} MB"
        
        return results
    
    def measure_tcp_settings(self) -> Dict:
        """
        Measure current TCP optimization settings.
        """
        print("Measuring TCP optimization settings...")
        
        results = {}
        
        settings = [
            "net.ipv4.tcp_congestion_control",
            "net.core.default_qdisc",
            "net.ipv4.tcp_fastopen",
            "net.ipv4.tcp_window_scaling",
            "net.ipv4.tcp_timestamps",
            "net.ipv4.tcp_low_latency",
            "net.ipv4.tcp_fin_timeout"
        ]
        
        for setting in settings:
            result = run(["sysctl", setting], timeout=2)
            if result["ok"]:
                value = result["stdout"].split("=")[1].strip()
                results[setting] = value
        
        results["available"] = True
        results["message"] = f"Congestion control: {results.get('net.ipv4.tcp_congestion_control', 'N/A')}, Qdisc: {results.get('net.core.default_qdisc', 'N/A')}"
        
        return results
    
    def run_full_benchmark(self) -> Dict:
        """
        Run all benchmarks and return comprehensive results.
        """
        print("\n" + "="*70)
        print("NETWORK PERFORMANCE BENCHMARK")
        print("="*70 + "\n")
        
        start_time = time.time()
        
        results = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "latency": self.measure_tcp_latency(),
            "connection_handling": self.measure_connection_handling(),
            "buffer_sizes": self.measure_buffer_sizes(),
            "tcp_settings": self.measure_tcp_settings(),
        }
        
        # Only run throughput test if explicitly requested (requires iperf3 server)
        # results["throughput"] = self.measure_tcp_throughput()
        
        results["benchmark_duration_seconds"] = time.time() - start_time
        
        return results
    
    def print_results(self, results: Dict):
        """
        Pretty print benchmark results.
        """
        print("\n" + "="*70)
        print("BENCHMARK RESULTS")
        print("="*70)
        print(f"\nTimestamp: {results['timestamp']}")
        print(f"Duration: {results['benchmark_duration_seconds']:.2f}s\n")
        
        # Latency
        if results['latency']['available']:
            print("Network Latency (ping to 8.8.8.8):")
            if 'avg_ms' in results['latency']:
                print(f"  Min: {results['latency']['min_ms']:.2f} ms")
                print(f"  Avg: {results['latency']['avg_ms']:.2f} ms")
                print(f"  Max: {results['latency']['max_ms']:.2f} ms")
            else:
                print(f"  {results['latency']['message']}")
        else:
            print(f"Network Latency: {results['latency']['message']}")
        
        # Connection Handling
        print("\nConnection Handling Capacity:")
        ch = results['connection_handling']
        if ch['available']:
            print(f"  TCP Max SYN Backlog: {ch.get('tcp_max_syn_backlog', 'N/A')}")
            print(f"  SYN Cookies Enabled: {ch.get('tcp_syncookies_enabled', 'N/A')}")
            print(f"  Max Listen Queue (somaxconn): {ch.get('somaxconn', 'N/A')}")
        
        # Buffer Sizes
        print("\nNetwork Buffer Sizes:")
        bs = results['buffer_sizes']
        if bs['available']:
            print(f"  Max Receive Buffer: {bs.get('net.core.rmem_max', 0) / 1024 / 1024:.2f} MB")
            print(f"  Max Send Buffer: {bs.get('net.core.wmem_max', 0) / 1024 / 1024:.2f} MB")
            print(f"  Default Receive Buffer: {bs.get('net.core.rmem_default', 0) / 1024:.2f} KB")
            print(f"  Default Send Buffer: {bs.get('net.core.wmem_default', 0) / 1024:.2f} KB")
        
        # TCP Settings
        print("\nTCP Optimization Settings:")
        ts = results['tcp_settings']
        if ts['available']:
            print(f"  Congestion Control: {ts.get('net.ipv4.tcp_congestion_control', 'N/A')}")
            print(f"  Default Qdisc: {ts.get('net.core.default_qdisc', 'N/A')}")
            print(f"  TCP Fast Open: {ts.get('net.ipv4.tcp_fastopen', 'N/A')}")
            print(f"  TCP Window Scaling: {ts.get('net.ipv4.tcp_window_scaling', 'N/A')}")
            print(f"  TCP Timestamps: {ts.get('net.ipv4.tcp_timestamps', 'N/A')}")
            print(f"  TCP Low Latency: {ts.get('net.ipv4.tcp_low_latency', 'N/A')}")
            print(f"  TCP FIN Timeout: {ts.get('net.ipv4.tcp_fin_timeout', 'N/A')}s")
        
        print("\n" + "="*70 + "\n")
    
    def save_results(self, results: Dict, filename: str = "benchmark_results.json"):
        """
        Save benchmark results to JSON file.
        """
        filepath = Path(__file__).parent / filename
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"Results saved to: {filepath}")


def compare_before_after(before_file: str, after_file: str):
    """
    Compare benchmark results before and after optimization.
    """
    print("\n" + "="*70)
    print("BEFORE vs AFTER COMPARISON")
    print("="*70 + "\n")
    
    before_path = Path(__file__).parent / before_file
    after_path = Path(__file__).parent / after_file
    
    if not before_path.exists():
        print(f"Error: Before benchmark file not found: {before_path}")
        return
    
    if not after_path.exists():
        print(f"Error: After benchmark file not found: {after_path}")
        return
    
    with open(before_path) as f:
        before = json.load(f)
    
    with open(after_path) as f:
        after = json.load(f)
    
    # Compare latency
    if before['latency']['available'] and after['latency']['available']:
        if 'avg_ms' in before['latency'] and 'avg_ms' in after['latency']:
            before_lat = before['latency']['avg_ms']
            after_lat = after['latency']['avg_ms']
            improvement = ((before_lat - after_lat) / before_lat) * 100
            
            print("Latency Comparison:")
            print(f"  Before: {before_lat:.2f} ms")
            print(f"  After:  {after_lat:.2f} ms")
            print(f"  Change: {improvement:+.1f}% ({'improvement' if improvement > 0 else 'regression'})\n")
    
    # Compare buffer sizes
    print("Buffer Size Changes:")
    before_bs = before['buffer_sizes']
    after_bs = after['buffer_sizes']
    
    for key in ['net.core.rmem_max', 'net.core.wmem_max']:
        if key in before_bs and key in after_bs:
            before_val = before_bs[key] / 1024 / 1024
            after_val = after_bs[key] / 1024 / 1024
            change = ((after_val - before_val) / before_val) * 100 if before_val > 0 else 0
            print(f"  {key}")
            print(f"    Before: {before_val:.2f} MB")
            print(f"    After:  {after_val:.2f} MB")
            print(f"    Change: {change:+.1f}%")
    
    # Compare connection settings
    print("\nConnection Handling Changes:")
    before_ch = before['connection_handling']
    after_ch = after['connection_handling']
    
    for key in ['tcp_max_syn_backlog']:
        if key in before_ch and key in after_ch:
            before_val = before_ch[key]
            after_val = after_ch[key]
            change = ((after_val - before_val) / before_val) * 100 if before_val > 0 else 0
            print(f"  {key}: {before_val} → {after_val} ({change:+.1f}%)")
    
    # Compare TCP settings
    print("\nTCP Settings Changes:")
    before_ts = before['tcp_settings']
    after_ts = after['tcp_settings']
    
    for key in ['net.ipv4.tcp_congestion_control', 'net.core.default_qdisc']:
        if key in before_ts and key in after_ts:
            before_val = before_ts[key]
            after_val = after_ts[key]
            if before_val != after_val:
                print(f"  {key}: {before_val} → {after_val}")
    
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Network Performance Benchmark")
    parser.add_argument("--output", "-o", default="benchmark_results.json",
                       help="Output JSON file for results")
    parser.add_argument("--compare", "-c", nargs=2, metavar=("BEFORE", "AFTER"),
                       help="Compare two benchmark result files")
    
    args = parser.parse_args()
    
    if args.compare:
        compare_before_after(args.compare[0], args.compare[1])
    else:
        benchmark = NetworkBenchmark()
        results = benchmark.run_full_benchmark()
        benchmark.print_results(results)
        benchmark.save_results(results, args.output)
