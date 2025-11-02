"""
Performance validation metrics for network configuration changes.
Measures latency, throughput, packet loss, and other performance indicators.
"""

import subprocess
import statistics
import time
import json
from typing import Dict, List, Optional


def _run_command(cmd: List[str], timeout: int = 30) -> tuple[bool, str, str]:
    """Run a command and return (success, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return (result.returncode == 0, result.stdout, result.stderr)
    except subprocess.TimeoutExpired:
        return (False, "", "Command timed out")
    except Exception as e:
        return (False, "", str(e))


def measure_latency(
    host: str = "8.8.8.8",
    count: int = 20,
    timeout: int = 30
) -> Dict:
    """
    Measure ICMP latency using ping.
    
    Args:
        host: Target host to ping (default: Google DNS)
        count: Number of ping packets to send
        timeout: Command timeout in seconds
    
    Returns:
        {
            "available": bool,
            "host": str,
            "count": int,
            "min_ms": float,
            "avg_ms": float,
            "max_ms": float,
            "jitter_ms": float,
            "packet_loss_percent": float,
            "raw_times": [float, ...],
            "message": str
        }
    """
    success, stdout, stderr = _run_command(["ping", "-c", str(count), "-W", "2", host], timeout)
    
    if not success:
        return {
            "available": False,
            "host": host,
            "message": f"Ping failed: {stderr}",
            "error": stderr
        }
    
    # Parse ping output
    times = []
    packets_sent = count
    packets_received = 0
    
    for line in stdout.split("\n"):
        # Extract time values from lines like: "64 bytes from 8.8.8.8: icmp_seq=1 ttl=117 time=14.2 ms"
        if "time=" in line:
            try:
                time_str = line.split("time=")[1].split()[0]
                times.append(float(time_str))
                packets_received += 1
            except (IndexError, ValueError):
                pass
        
        # Extract packet loss from statistics line
        if "packets transmitted" in line:
            # Format: "20 packets transmitted, 20 received, 0% packet loss, time 19023ms"
            parts = line.split(",")
            for part in parts:
                if "transmitted" in part:
                    packets_sent = int(part.split()[0])
                if "received" in part:
                    packets_received = int(part.split()[0])
    
    if not times:
        return {
            "available": False,
            "host": host,
            "message": "No ping responses received",
            "packet_loss_percent": 100.0
        }
    
    packet_loss = ((packets_sent - packets_received) / packets_sent) * 100
    
    return {
        "available": True,
        "host": host,
        "count": len(times),
        "min_ms": min(times),
        "avg_ms": statistics.mean(times),
        "max_ms": max(times),
        "jitter_ms": max(times) - min(times),
        "stddev_ms": statistics.stdev(times) if len(times) > 1 else 0.0,
        "packet_loss_percent": packet_loss,
        "raw_times": times,
        "message": f"Latency: avg={statistics.mean(times):.2f}ms, jitter={max(times) - min(times):.2f}ms, loss={packet_loss:.1f}%"
    }


def measure_multi_host_latency(
    hosts: Optional[List[str]] = None,
    count: int = 10
) -> Dict:
    """
    Measure latency to multiple hosts and return aggregated results.
    
    Args:
        hosts: List of hosts to test (default: common DNS servers)
        count: Number of pings per host
    
    Returns:
        {
            "available": bool,
            "tests": {host: {...}, ...},
            "average_latency_ms": float,
            "best_host": str,
            "worst_host": str
        }
    """
    if hosts is None:
        hosts = ["8.8.8.8", "1.1.1.1", "9.9.9.9"]  # Google, Cloudflare, Quad9
    
    results = {}
    latencies = []
    
    for host in hosts:
        result = measure_latency(host=host, count=count)
        results[host] = result
        if result.get("available"):
            latencies.append((host, result["avg_ms"]))
    
    if not latencies:
        return {
            "available": False,
            "tests": results,
            "message": "All latency tests failed"
        }
    
    avg_latency = statistics.mean([lat for _, lat in latencies])
    best_host = min(latencies, key=lambda x: x[1])
    worst_host = max(latencies, key=lambda x: x[1])
    
    return {
        "available": True,
        "tests": results,
        "average_latency_ms": avg_latency,
        "best_host": best_host[0],
        "best_latency_ms": best_host[1],
        "worst_host": worst_host[0],
        "worst_latency_ms": worst_host[1],
        "message": f"Average latency: {avg_latency:.2f}ms (best: {best_host[0]} @ {best_host[1]:.2f}ms)"
    }


def measure_tcp_throughput(
    host: str = "127.0.0.1",
    port: int = 5001,
    duration: int = 5
) -> Dict:
    """
    Measure TCP throughput using iperf3 (if available).
    
    Args:
        host: iperf3 server address
        port: iperf3 server port
        duration: Test duration in seconds
    
    Returns:
        {
            "available": bool,
            "throughput_mbps": float,
            "retransmits": int,
            "message": str
        }
    """
    # Check if iperf3 is installed
    success, stdout, stderr = _run_command(["which", "iperf3"], timeout=2)
    if not success:
        return {
            "available": False,
            "message": "iperf3 not installed. Install with: sudo apt-get install iperf3"
        }
    
    # Run iperf3 test
    success, stdout, stderr = _run_command(
        ["iperf3", "-c", host, "-p", str(port), "-t", str(duration), "-J"],
        timeout=duration + 10
    )
    
    if not success:
        return {
            "available": True,
            "installed": True,
            "server_available": False,
            "message": f"iperf3 server not available at {host}:{port}. Start server with: iperf3 -s"
        }
    
    try:
        data = json.loads(stdout)
        throughput = data["end"]["sum_received"]["bits_per_second"] / 1_000_000
        retransmits = data["end"]["sum_sent"].get("retransmits", 0)
        
        return {
            "available": True,
            "throughput_mbps": throughput,
            "retransmits": retransmits,
            "duration_seconds": duration,
            "message": f"Throughput: {throughput:.2f} Mbps, Retransmits: {retransmits}"
        }
    except (json.JSONDecodeError, KeyError) as e:
        return {
            "available": True,
            "error": str(e),
            "message": "Failed to parse iperf3 output"
        }


def measure_connection_time(
    url: str = "https://www.google.com",
    count: int = 5
) -> Dict:
    """
    Measure TCP connection establishment time using curl.
    
    Args:
        url: URL to connect to
        count: Number of connection attempts
    
    Returns:
        {
            "available": bool,
            "avg_connect_ms": float,
            "min_connect_ms": float,
            "max_connect_ms": float,
            "message": str
        }
    """
    # Check if curl is available
    success, stdout, stderr = _run_command(["which", "curl"], timeout=2)
    if not success:
        return {
            "available": False,
            "message": "curl not installed"
        }
    
    connect_times = []
    
    for _ in range(count):
        success, stdout, stderr = _run_command(
            ["curl", "-o", "/dev/null", "-s", "-w", "%{time_connect}", url],
            timeout=10
        )
        
        if success:
            try:
                # curl returns time in seconds, convert to ms
                connect_time_ms = float(stdout.strip()) * 1000
                connect_times.append(connect_time_ms)
            except ValueError:
                pass
        
        # Small delay between requests
        time.sleep(0.5)
    
    if not connect_times:
        return {
            "available": True,
            "message": f"Failed to connect to {url}"
        }
    
    return {
        "available": True,
        "url": url,
        "count": len(connect_times),
        "avg_connect_ms": statistics.mean(connect_times),
        "min_connect_ms": min(connect_times),
        "max_connect_ms": max(connect_times),
        "message": f"Connection time: avg={statistics.mean(connect_times):.2f}ms"
    }


def measure_dns_resolution(
    domain: str = "google.com",
    server: str = "8.8.8.8",
    count: int = 5
) -> Dict:
    """
    Measure DNS resolution time using dig.
    
    Args:
        domain: Domain to resolve
        server: DNS server to query
        count: Number of queries
    
    Returns:
        {
            "available": bool,
            "avg_query_ms": float,
            "min_query_ms": float,
            "max_query_ms": float,
            "message": str
        }
    """
    # Check if dig is available
    success, stdout, stderr = _run_command(["which", "dig"], timeout=2)
    if not success:
        return {
            "available": False,
            "message": "dig not installed. Install with: sudo apt-get install dnsutils"
        }
    
    query_times = []
    
    for _ in range(count):
        success, stdout, stderr = _run_command(
            ["dig", f"@{server}", domain, "+stats"],
            timeout=5
        )
        
        if success:
            # Parse output for query time
            for line in stdout.split("\n"):
                if "Query time:" in line:
                    try:
                        # Format: ";; Query time: 14 msec"
                        time_str = line.split("Query time:")[1].split("msec")[0].strip()
                        query_times.append(float(time_str))
                    except (IndexError, ValueError):
                        pass
        
        time.sleep(0.2)
    
    if not query_times:
        return {
            "available": True,
            "message": f"Failed to query DNS for {domain}"
        }
    
    return {
        "available": True,
        "domain": domain,
        "server": server,
        "count": len(query_times),
        "avg_query_ms": statistics.mean(query_times),
        "min_query_ms": min(query_times),
        "max_query_ms": max(query_times),
        "message": f"DNS query time: avg={statistics.mean(query_times):.2f}ms"
    }


def run_full_benchmark(profile: str = "gaming") -> Dict:
    """
    Run a comprehensive set of network performance tests.
    
    Args:
        profile: Test profile (gaming, throughput, balanced)
    
    Returns:
        {
            "profile": str,
            "timestamp": str,
            "latency": {...},
            "connection_time": {...},
            "dns_resolution": {...},
            "throughput": {...},  # Optional, if iperf3 available
            "summary": str
        }
    """
    import datetime
    
    results = {
        "profile": profile,
        "timestamp": datetime.datetime.now().isoformat(),
        "tests": {}
    }
    
    # Adjust test parameters based on profile
    if profile == "gaming":
        # Gaming: Focus on latency and jitter, more ping samples
        latency_result = measure_latency(host="8.8.8.8", count=30)
        results["tests"]["latency"] = latency_result
        
        # Test to multiple gaming-relevant servers
        multi_latency = measure_multi_host_latency(
            hosts=["8.8.8.8", "1.1.1.1"],
            count=15
        )
        results["tests"]["multi_latency"] = multi_latency
        
    elif profile == "throughput":
        # Throughput: Focus on bandwidth, include iperf3
        latency_result = measure_latency(host="8.8.8.8", count=10)
        results["tests"]["latency"] = latency_result
        
        throughput_result = measure_tcp_throughput(duration=10)
        results["tests"]["throughput"] = throughput_result
        
    else:  # balanced
        # Balanced: All tests with moderate samples
        latency_result = measure_latency(host="8.8.8.8", count=20)
        results["tests"]["latency"] = latency_result
    
    # Common tests for all profiles
    connection_result = measure_connection_time(count=5)
    results["tests"]["connection_time"] = connection_result
    
    dns_result = measure_dns_resolution(count=5)
    results["tests"]["dns_resolution"] = dns_result
    
    # Generate summary
    summary_parts = []
    if results["tests"]["latency"].get("available"):
        lat = results["tests"]["latency"]
        summary_parts.append(f"Latency: {lat['avg_ms']:.2f}ms (jitter: {lat['jitter_ms']:.2f}ms)")
    
    if results["tests"]["connection_time"].get("available"):
        conn = results["tests"]["connection_time"]
        summary_parts.append(f"Connection: {conn['avg_connect_ms']:.2f}ms")
    
    if results["tests"].get("throughput", {}).get("available"):
        tp = results["tests"]["throughput"]
        summary_parts.append(f"Throughput: {tp['throughput_mbps']:.2f} Mbps")
    
    results["summary"] = " | ".join(summary_parts) if summary_parts else "No tests available"
    
    return results


def quick_latency_test() -> Dict:
    """
    Quick latency test for rapid validation (10 pings).
    Useful for fast before/after comparisons.
    """
    return measure_latency(host="8.8.8.8", count=10, timeout=15)
