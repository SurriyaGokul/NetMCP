<div align="center">

# 🌐 NetMCP

### AI-Powered Linux Network Optimization via Model Context Protocol

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-Enabled-00ADD8?style=for-the-badge&logo=anthropic&logoColor=white)](https://modelcontextprotocol.io/)
[![Linux](https://img.shields.io/badge/Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black)](https://www.linux.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)
[![Live on FastMCP](https://img.shields.io/badge/Live-FastMCP%20Cloud-FF6B6B?style=for-the-badge&logo=cloud&logoColor=white)](https://netmcp.fastmcp.app/mcp)

**Transform natural language into optimized network configurations**

[🔴 Live Server](#-live-server) · [Getting Started](#-getting-started) · [Features](#-features) · [Profiles](#-optimization-profiles) · [Architecture](#-architecture) · [Tools](#-mcp-tools)

</div>

---

## 🔴 Live Server

NetMCP is **live in production** on FastMCP Cloud! Connect your MCP client to:

```
https://netmcp.fastmcp.app/mcp
```

No installation required—just point your AI assistant to the hosted server and start optimizing.

---

## 🎯 Overview

NetMCP is an **MCP server** that enables AI assistants like Claude to intelligently optimize Linux network performance. It bridges the gap between high-level optimization goals (*"optimize my network for gaming"*) and low-level Linux commands (`sysctl`, `tc`, `nft`).

```
┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
│   AI Assistant   │ MCP  │     NetMCP       │      │   Linux Kernel   │
│   (Claude, etc)  │◄────►│   Server         │─────►│   Network Stack  │
└──────────────────┘      └──────────────────┘      └──────────────────┘
         ▲                         │
         │                         ▼
    Natural Language        29 Config Cards
    "Reduce my latency"     5 Profiles
                            40+ Tools
```

### ✨ Why NetMCP?

| Traditional Approach | With NetMCP |
|---------------------|-------------|
| Manual `sysctl` tuning | Declarative optimization plans |
| Copy-paste commands from forums | Research-backed profiles |
| No rollback on failure | Automatic checkpoints & rollback |
| Trial and error | Validated against safety policies |
| Root access chaos | Controlled privileged execution |

---

## 🚀 Getting Started

### Prerequisites

- **Linux** (Ubuntu 20.04+, Debian 11+, or similar)
- **Python 3.10+**
- Network tools: `ip`, `sysctl`, `tc`, `nft`

### Installation

```bash
git clone https://github.com/SurriyaGokul/mcp-net-optimizer.git
cd mcp-net-optimizer

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Enable privileged commands (one-time setup)
./setup_sudo.sh
```

### Configure with Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "netmcp": {
      "command": "python",
      "args": ["-m", "server.main"],
      "cwd": "/path/to/mcp-net-optimizer"
    }
  }
}
```

### Run Standalone

```bash
python -m server.main
```

---

## ⚡ Features

<table>
<tr>
<td width="50%">

### 🎴 29 Configuration Cards

Full coverage of the Linux networking stack:

- **16 Sysctl cards** — TCP tuning, buffers, congestion control
- **8 Traffic Control cards** — QoS, shaping, queuing
- **5 Firewall cards** — Rate limiting, connection tracking, NAT

</td>
<td width="50%">

### 🛡️ Enterprise Safety

Production-ready security features:

- **Command allowlisting** — Only approved binaries execute
- **Automatic checkpoints** — Snapshot before every change
- **Instant rollback** — One command to restore state
- **Audit logging** — Complete execution history

</td>
</tr>
<tr>
<td>

### 🔧 40+ MCP Tools

Comprehensive network management:

- **Discovery** — Interfaces, routes, DNS, latency tests
- **Planning** — Type-safe optimization plans
- **Validation** — Policy enforcement before execution
- **Execution** — Atomic apply with rollback
- **Benchmarking** — Before/after performance comparison

</td>
<td>

### 🔐 Sudo Management

Flexible privilege escalation:

- **Passwordless setup** — Run `./setup_sudo.sh` once
- **Cached credentials** — Authenticate once, cached 15 min
- **MCP tools** — `check_sudo_access`, `request_sudo_access`
- **Secure by default** — Only allowlisted commands

</td>
</tr>
</table>

---

## 🎮 Optimization Profiles

Five research-backed profiles optimized for specific workloads:

| Profile | Focus | Key Optimizations | Target Metrics |
|---------|-------|-------------------|----------------|
| 🎮 **Gaming** | Ultra-low latency | BBR, tcp_low_latency, fq qdisc | <20ms p95, <5ms jitter |
| 📺 **Streaming** | Max throughput | Large buffers, BBR, HTB shaping | 90%+ link utilization |
| 📞 **Video Calls** | Balanced | DSCP marking, moderate buffers | <150ms latency (ITU-T) |
| 📦 **Bulk Transfer** | Maximum bandwidth | 128MB buffers, aggressive BBR | >1Gbps sustained |
| 🖥️ **Server** | High concurrency | SYN cookies, conntrack, rate limits | 10K+ connections |

### Example: Gaming Optimization

```python
plan = {
    "iface": "eth0",
    "profile": "gaming",
    "changes": {
        "sysctl": {
            "net.ipv4.tcp_congestion_control": "bbr",
            "net.ipv4.tcp_low_latency": "1",
            "net.core.default_qdisc": "fq"
        },
        "qdisc": {"type": "fq"}
    }
}
```

---

## 🏗️ Architecture

### Pipeline Flow

```
  DISCOVER          PLAN            VALIDATE         RENDER           APPLY
 ┌─────────┐    ┌─────────┐      ┌─────────┐     ┌─────────┐     ┌─────────┐
 │ Inspect │───►│ Declare │─────►│ Check   │────►│Generate │────►│ Execute │
 │ System  │    │ Intent  │      │ Policies│     │Commands │     │ Safely  │
 └─────────┘    └─────────┘      └─────────┘     └─────────┘     └─────────┘
      │              │                │               │               │
   30+ tools    Pydantic         Policy YAML      sysctl/tc/     Checkpoint
   No side      schemas          validation       nft scripts    + Rollback
   effects
```

### Project Structure

```
mcp-net-optimizer/
├── server/
│   ├── main.py              # MCP server entry point
│   ├── registry.py          # Tool & resource registration
│   ├── schema/models.py     # Pydantic data models
│   └── tools/
│       ├── discovery.py     # 30+ system inspection tools
│       ├── planner.py       # Plan → Commands renderer
│       ├── validator.py     # Policy validation
│       ├── validation_engine.py  # Before/after comparison
│       ├── validation_metrics.py # Network benchmarks
│       ├── audit_log.py     # Execution logging
│       ├── apply/           # Command executors
│       │   ├── apply.py     # Orchestration + rollback
│       │   ├── checkpoints.py
│       │   ├── sysctl.py
│       │   ├── tc.py
│       │   └── nft.py
│       └── util/
│           ├── shell.py     # Safe command execution
│           └── policy_loader.py
├── policy/
│   ├── config_cards/        # 29 YAML card definitions
│   ├── profiles.yaml        # 5 optimization profiles
│   └── validation_limits.yaml
└── setup_sudo.sh            # Passwordless sudo setup
```

---

## 🔧 MCP Tools

### Discovery (No Side Effects)

| Tool | Description |
|------|-------------|
| `ip_info` | Network interfaces and addresses |
| `ip_route` | Routing table |
| `ping_host` | ICMP latency test |
| `traceroute` | Network path analysis |
| `tc_qdisc_show` | Traffic control status |
| `nft_list_ruleset` | Firewall rules |
| `ss_summary` | Socket statistics |

### Planning & Validation

| Tool | Description |
|------|-------------|
| `validate_change_plan_tool` | Validate plan against policies |
| `render_change_plan_tool` | Convert plan to executable commands |
| `test_network_performance_tool` | Run comprehensive benchmarks |
| `validate_configuration_changes_tool` | Compare before/after results |

### Execution & Safety

| Tool | Description |
|------|-------------|
| `apply_rendered_plan_tool` | Execute with checkpoint + rollback |
| `snapshot_checkpoint_tool` | Manual checkpoint creation |
| `rollback_to_checkpoint_tool` | Restore previous state |
| `list_checkpoints_tool` | View available checkpoints |

### Privilege Management

| Tool | Description |
|------|-------------|
| `check_sudo_access_tool` | Check if sudo is available |
| `request_sudo_access_tool` | Authenticate for temporary access |
| `get_sudo_setup_instructions_tool` | Setup help |

---

## 📊 Benchmarking & Validation

NetMCP includes a complete validation pipeline to measure optimization impact:

```python
# 1. Run baseline benchmark
before = test_network_performance_tool(profile="gaming")

# 2. Apply optimizations
apply_rendered_plan_tool(rendered_plan)

# 3. Run post-optimization benchmark  
after = test_network_performance_tool(profile="gaming")

# 4. Compare and validate
result = validate_configuration_changes_tool(before, after, "gaming")
# → {"decision": "KEEP", "score": 75, "summary": "Latency improved 15%"}
```

### Validation Decisions

| Score | Decision | Action |
|-------|----------|--------|
| ≥60 | **KEEP** | Changes improved performance |
| 20-59 | **UNCERTAIN** | Mixed results, review recommended |
| <20 | **ROLLBACK** | Performance degraded, auto-rollback available |

---

## 🔒 Security Model

### Command Allowlisting

Only explicitly approved binaries can execute:

```yaml
# server/config/allowlist.yaml
binaries:
  - /usr/sbin/sysctl
  - /usr/sbin/tc
  - /usr/sbin/nft
  - /usr/bin/ping
  - /usr/bin/iperf3
  # ... etc
```

### Privilege Escalation

Three options for sudo access:

1. **Permanent** (Recommended): Run `./setup_sudo.sh` — configures passwordless sudo for network commands only
2. **Session-based**: Use `request_sudo_access_tool(password="...")` — caches for 15 minutes
3. **Manual**: Run `sudo -v` in terminal before using MCP

---

## 📈 Performance Results

Real-world improvements measured across profiles:

| Profile | Metric | Improvement |
|---------|--------|-------------|
| Gaming | Latency | 10-30% reduction |
| Gaming | Jitter | 20-40% reduction |
| Streaming | Throughput | 2-4× on congested links |
| Video Calls | Connection time | 15-25% faster |
| Server | Connection capacity | 10× increase |

---

## 🤝 Contributing

Contributions are welcome! Areas of interest:

- Additional configuration cards
- New optimization profiles
- Cross-platform support
- Performance benchmarks
- Documentation improvements

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

**Built with ❤️ for the AI-native networking future**

[Report Bug](https://github.com/SurriyaGokul/mcp-net-optimizer/issues) · [Request Feature](https://github.com/SurriyaGokul/mcp-net-optimizer/issues)

</div>
