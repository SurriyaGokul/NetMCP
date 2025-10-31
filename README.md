# MCP Network Optimizer 

Intelligent, safe, and practical network optimization via Model Context Protocol (MCP). This server exposes discovery, planning, validation, and application tools so an MCP client (LLM/agent) can inspect your system, design an optimization plan, validate it against policy, and render/apply real commands with safeguards.

## Highlights

- Full MCP server powered by FastMCP with 30+ tools and policy resources
- Structured policy “configuration cards” for sysctl, tc, nftables, offloads, MTU
- Pydantic schemas for plan, rendering, and change reports (typed, validated)
- Safe execution: allowlisted binaries, dry-run previews, checkpoint/rollback hooks
- Real commands generated: sysctl, tc, nft -f, ethtool -K, ip link
- Practical scenarios: gaming (low latency), high‑throughput servers, QoS/HTB, VPN/NAT, DDoS hardening
- Benchmarks and demos included


## Table of contents

- Overview
- Architecture
- Policy model and resources
- MCP tools catalog
- Installation
- Running the MCP server
- Usage examples
- Benchmarking and results
- Testing and demo
- Security and safety
- Project structure
- Next steps


## Overview 

MCP Network Optimizer is an MCP server that helps an LLM or agent optimize Linux networking:

1) Discover: Inspect interfaces, routes, DNS, latency, qdisc, firewall rules.
2) Plan: Describe “what you want” using a ParameterPlan (Pydantic) schema.
3) Validate: Check the plan against schema/policies and constraints.
4) Render: Turn plans into concrete command lines and scripts.
5) Apply: Execute commands safely with checkpoint/rollback hooks.


## Architecture 

- Server runtime: `fastmcp` (Model Context Protocol) in `server/main.py`
- Resource and tool registry: `server/registry.py`
- Policy registry and loader: `server/tools/util/policy_loader.py`
- Validation schemas (Pydantic): `server/schema/models.py`
- Planning and validation: `server/tools/planner.py`, `server/tools/validator.py`
- Apply modules (idempotent, allowlisted exec):
	- Sysctl: `server/tools/apply/sysctl.py`
	- Traffic control (tc): `server/tools/apply/tc.py`
	- Nftables: `server/tools/apply/nft.py`
	- NIC offloads (ethtool): `server/tools/apply/offloads.py`
	- MTU: `server/tools/apply/mtu.py`
	- Orchestrator & checkpoints: `server/tools/apply/apply.py`, `server/tools/apply/checkpoints.py`
- Discovery suite: `server/tools/discovery.py`
- Command allowlist: `server/config/allowlist.yaml`
- Policy config cards (YAML): `policy/config_cards/*.yaml`

Key schemas (`server/schema/models.py`):
- ParameterPlan: iface, profile, changes (sysctl, qdisc/shaper, dscp, offloads, mtu), validate, rationale
- RenderedPlan: sysctl_cmds[], tc_script, nft_script, ethtool_cmds[], ip_link_cmds[]
- ValidationResult: ok, issues[], normalized_plan
- ChangeReport: applied, dry_run, errors[], checkpoint_id, notes[]


## Policy model and MCP resources 

Policy is expressed as “configuration cards” (YAML) with limits and profiles.

- Cards live in `policy/config_cards/` and cover:
	- TCP/IP tuning: congestion control, buffers, timeouts, syncookies, timestamps, scaling
	- Traffic Control (tc): qdisc types (fq_codel, CAKE, HTB), shaping, priorities
	- Firewall/QoS: nftables DSCP marking, connection tracking, NAT
	- NIC: offloads (GRO/GSO/TSO/LRO), MTU

Exposed as MCP resources (see `server/registry.py`):
- `policy://config_cards/list` — list all available config cards (count + IDs)
- `policy://config_cards/{card_id}` — fetch a card’s full details


## MCP tools catalog 

Discovery (no side effects):
- ip_info, eth_info, hostname_ips, hostnamectl
- nmcli_status, iwconfig, iwlist_scan
- arp_table, ip_neigh, ip_route
- resolvectl_status, cat_resolv_conf
- dig, host, nslookup
- ping_host, traceroute, tracepath
- ss_summary, tc_qdisc_show
- nft_list_ruleset, iptables_list

Planning/validation:
- validate_change_plan_tool(parameter_plan: dict) → ValidationResult
- render_change_plan_tool(plan: dict) → RenderedPlan

Apply and safety:
- apply_rendered_plan_tool(rendered_plan: dict, checkpoint_label?: str) → ChangeReport
- snapshot_checkpoint_tool(label?: str) → { checkpoint_id }
- rollback_to_checkpoint_tool(checkpoint_id: str)

Direct apply helpers (also registered as MCP tools):
- set_sysctl(kv: dict[str,str])
- apply_tc_script(lines: list[str])
- apply_nft_ruleset(ruleset: str)
- set_nic_offloads(iface: str, flags: dict[str,bool])
- set_mtu(iface: str, mtu: int)


## Installation 

Prerequisites: Linux, Python 3.10+, standard networking tools (ip, sysctl, tc, nft, ethtool). Optional: NetworkManager (nmcli), wireless-tools (iwconfig/iwlist), dnsutils (dig/host/nslookup), traceroute.

Install Python dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```


## Running the MCP server 

From the repository root:

```bash
python -m server.main
```

This starts “MCP Network Optimizer” via FastMCP, exposing the tools/resources listed above to your MCP client.

MCP client integration: Configure your MCP-capable client (e.g., an agent/IDE that supports MCP) to launch this server and call tools/resources. Refer to your client’s documentation for adding external MCP servers (executable: `python -m server.main`).


## Usage examples 

Programmatic (local Python) usage for planning, validation, rendering, and preview:

```python
from server.tools.validator import validate_change_plan
from server.tools.planner import render_change_plan

plan = {
		"iface": "eth0",
		"profile": "gaming",
		"changes": {
				"sysctl": {
						"net.ipv4.tcp_low_latency": "1",
						"net.ipv4.tcp_fastopen": "3",
						"net.core.netdev_budget": "600",
						"net.ipv4.tcp_fin_timeout": "10"
				}
		},
		"rationale": ["Optimize for low latency"]
}

validation = validate_change_plan(plan)
assert validation["ok"], validation["errors"]

rendered = render_change_plan(plan)
print("sysctl:", rendered["sysctl_cmds"])        # preview commands
print("tc script:\n", rendered["tc_script"])     # preview script
```

Applying changes safely (requires root privileges for most commands):

```python
from server.tools.apply.apply import apply_rendered_plan

report = apply_rendered_plan(rendered, checkpoint_label="pre-gaming-opt")
print(report["applied"], report["errors"], report["checkpoint_id"])
```

Note: The checkpoint/rollback hooks are stubbed and ready for integration (see `server/tools/apply/checkpoints.py`).


## Benchmarking and results 

Scripts: `server/tests/benchmark.py`, baseline data: `server/tests/baseline_benchmark.json`.

Quick start:

```bash
# Baseline
python server/tests/benchmark.py -o baseline.json

# After applying an optimization
python server/tests/benchmark.py -o after.json

# Compare
python server/tests/benchmark.py --compare baseline.json after.json
```

Executive summary 
- Discovery, validation, rendering, and integration flows are working end-to-end
- 29+ configuration cards cover sysctl, tc, nftables, offloads, and MTU
- Multiple scenarios validated: low-latency gaming, high-throughput servers, QoS/HTB, VPN/NAT, DDoS hardening

Measured baseline (from included benchmark script):
- Latency (ping to 8.8.8.8): ~18.36 ms avg
- Buffer sizes: rmem_max ≈ 16 MB, wmem_max ≈ 16 MB
- TCP baseline: congestion control=cubic, default qdisc=fq_codel, fastopen=1, window scaling=1, timestamps=on, low_latency=0, FIN timeout=60s, SYN backlog=1024

Results at a glance 
- Low‑latency gaming profile: 10–30% latency reduction expected; 15–25% faster connection setup; 30–50% faster connection recycling
- High‑throughput server profile: 2–4× throughput on lossy networks (BBR); +20–50% on clean links; smoother bursts with larger buffers (128 MB)
- QoS/HTB shaping: controlled bandwidth, fair queuing, reduced bufferbloat, lower latency under load

Example outcomes from demo scenarios:
- Gaming (sysctl low_latency=1, fastopen=3, netdev_budget=600, fin_timeout=10s)
	- Example before→after avg latency: 15.2 ms → 12.8 ms (~+15.8% improvement)
- File server (rmem_max/wmem_max=128 MB, BBR, qdisc=fq)
	- Expected: 2–4× throughput on lossy paths, +20–50% on high‑bandwidth clean links
- QoS/HTB @ 100 Mbit
	- Expected: predictable bandwidth sharing, reduced queues/backlog under load


## Testing and demo 

Run the full suite and demos:

```bash
# All-in-one test runner
./server/tests/run_all_tests.sh

# Integration tests
pytest server/tests/test_integration.py -v -s

# Scenario tests
pytest server/tests/test_real_world_scenarios.py -v -s

# Demo of capabilities
python server/tests/demo.py
```

What tests cover:
- Discovery tool correctness and structured responses
- Policy registry loads 29+ configuration cards
- Schema + policy validation for ParameterPlans
- Rendering to sysctl/tc/ethtool/nft/ip commands
- Scenario plans: gaming, server, QoS, VPN/NAT, DDoS hardening


## Security and safety 

- Command allowlisting via `server/config/allowlist.yaml`
- Schema validation and policy limits before execution
- No shell metacharacter injection; commands executed as argv arrays
- Checkpoint/rollback hooks to revert on failure (extensible)
- Strong recommendation to run the server as non‑root; elevate only specific commands as needed


## Project structure 

Key paths:
- Server entrypoint: `server/main.py`
- Tools registry: `server/registry.py`
- Schemas: `server/schema/models.py`
- Discovery: `server/tools/discovery.py`
- Planner/validator: `server/tools/planner.py`, `server/tools/validator.py`
- Apply modules: `server/tools/apply/*.py`
- Policy cards: `policy/config_cards/*.yaml`
- Tests, demos, benchmarks: `server/tests/*`


## Next steps 

- Integrate real checkpoint/rollback (currently stubbed)
- Add performance benchmarking suite with iperf3/netperf orchestration
- Expand configuration cards (IPv6, namespaces, container networking)
- Enhance discovery (auto-detect qdisc/hardware capabilities)
- Optional UI: progress indicators, web dashboard, and historical tracking


---
