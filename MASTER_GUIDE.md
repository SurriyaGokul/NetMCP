# 🎓 Complete MCP Network Optimizer Master Guide

## 📋 Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [The Policy System](#policy-system)
3. [Data Models & Schemas](#data-models)
4. [The Planning Pipeline](#planning-pipeline)
5. [Execution & Safety](#execution-safety)
6. [MCP Server Integration](#mcp-integration)
7. [Complete Flow Examples](#flow-examples)
8. [Advanced Topics](#advanced-topics)

---

## 1. Architecture Overview 🏗️

### What is This System?

**MCP Network Optimizer** is an intelligent network configuration system that:
- Listens as an MCP (Model Context Protocol) server
- Accepts high-level optimization requests from LLMs/agents
- Translates them to safe Linux network commands
- Executes with rollback protection

### The Big Picture

```
┌─────────────────────────────────────────────────────────────┐
│                    LLM / AI Agent                            │
│            (Claude, GPT-4, etc. via MCP)                     │
└────────────────┬────────────────────────────────────────────┘
                 │ MCP Protocol (JSON-RPC)
                 ↓
┌─────────────────────────────────────────────────────────────┐
│                    MCP Server (FastMCP)                      │
│  ┌──────────────────────────────────────────────────────┐   │
│  │            Registry (server/registry.py)             │   │
│  │  - Registers Tools (functions LLM can call)          │   │
│  │  - Registers Resources (data LLM can read)           │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────────────────┐
│                   Policy System                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Config Cards (29 cards)    Profiles (5 profiles)   │   │
│  │  - sysctl.tcp_*            - gaming                  │   │
│  │  - tc.htb_*                - streaming               │   │
│  │  - iptables.*              - video_calls             │   │
│  │                            - bulk_transfer           │   │
│  │                            - server                  │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────────────────┐
│              Processing Pipeline                             │
│                                                              │
│  1. VALIDATE → 2. PLAN → 3. RENDER → 4. APPLY              │
│                                                              │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │ Validator  │→ │  Planner   │→ │   Apply    │            │
│  │ Check      │  │ Translate  │  │ Execute    │            │
│  │ Rules      │  │ to Commands│  │ Commands   │            │
│  └────────────┘  └────────────┘  └────────────┘            │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────────────────┐
│                    Linux Kernel                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  sysctl  │  tc  │  nftables  │  ethtool  │  ip link │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Key Design Principles

1. **Declarative**: User describes *what* they want, not *how*
2. **Safe**: Checkpoints before changes, rollback on failure
3. **Policy-Driven**: All changes validated against rules
4. **Type-Safe**: Pydantic models ensure data validity
5. **Auditable**: Every change logged and traceable

---

## 2. The Policy System 📚

### What Are Config Cards?

Config cards are YAML files that describe individual network optimizations.

**Location**: `policy/config_cards/*.yaml`

**Example**: `sysctl_tcp_congestion_control.yaml`

```yaml
- id: sysctl.tcp_congestion_control
  category: sysctl
  subcategory: tcp_performance
  
  name: "TCP Congestion Control Algorithm"
  description: "Select the TCP congestion control algorithm"
  
  purpose: |
    Determines how TCP responds to network congestion.
    Modern algorithms like BBR can significantly improve performance.
  
  use_cases:
    primary:
      - name: "High-Bandwidth Networks"
        reason: "Optimize for maximum throughput"
        priority: "high"
  
  impact:
    throughput: "↑↑"    # Significant increase
    latency: "↑"        # Moderate improvement
    cpu_usage: "~"      # Neutral
  
  configuration:
    command_template: "sysctl -w net.ipv4.tcp_congestion_control={algorithm}"
    
    examples:
      - description: "High-performance server (BBR)"
        command: "sysctl -w net.ipv4.tcp_congestion_control=bbr"
        params:
          algorithm: "bbr"
  
  parameters:
    - name: "algorithm"
      type: "string"
      default: "bbr"
      valid_values: ["bbr", "cubic", "reno", "vegas"]
```

### The 29 Config Cards

**Sysctl Cards (16)**:
- TCP tuning: congestion_control, low_latency, fastopen, timestamps, window_scaling
- Buffers: tcp_rmem, tcp_wmem, core_rmem_max, core_wmem_max
- Connection management: fin_timeout, max_syn_backlog, syncookies
- Other: netdev_budget, ip_local_port_range, default_qdisc, ip_forward

**TC Cards (8)**:
- Qdisc types: qdisc_type (fq, cake, htb, fq_codel, pfifo_fast)
- HTB: htb_rate, htb_ceil, htb_priority, default_class
- Netem: netem_delay, netem_loss

**IPTables/NFTables Cards (5)**:
- connection_limiting: Limit connections per IP
- connection_tracking: Track connection states
- connection_tracking_size: Conntrack table size
- rate_limiting: Packet rate limits
- qos_marking: DSCP QoS marking
- nat: NAT rules (SNAT, DNAT, masquerade)

### What Are Profiles?

Profiles group config cards for specific use cases.

**Location**: `policy/profiles.yaml`

**The 5 Profiles**:

```yaml
1. Gaming Profile
   - Goal: Ultra-low latency (<20ms)
   - Cards: BBR, tcp_low_latency, small buffers, priority queueing
   - Use: FPS games, MOBAs, competitive gaming

2. Streaming Profile
   - Goal: Maximum throughput
   - Cards: BBR, large buffers, high netdev_budget
   - Use: Video servers, CDN nodes

3. Video Calls Profile
   - Goal: Balanced latency + throughput
   - Cards: BBR, QoS marking, moderate buffers
   - Use: Zoom, WebRTC, VoIP

4. Bulk Transfer Profile
   - Goal: Absolute max throughput
   - Cards: BBR, maximum buffers, expanded ports
   - Use: Backups, data replication

5. Server Profile
   - Goal: High concurrency + security
   - Cards: Connection limits, rate limits, fast socket reuse
   - Use: Web servers, APIs, high-traffic apps
```

### Rules and Limits

**Location**: `policy/rules.yaml`, `policy/limits.yaml`, `policy/validation_limits.yaml`

These define:
- What values are allowed (min/max ranges)
- Which cards can be combined
- Safety constraints
- Validation rules

---

## 3. Data Models & Schemas 🏗️

### The Pydantic Models

**Location**: `server/schema/models.py`

These are the core data structures that flow through the system:

### 3.1 ParameterPlan (User Input)

This is what the LLM/user provides:

```python
class ParameterPlan(BaseModel):
    iface: str                    # Network interface (e.g., "eth0")
    profile: str                  # Profile name (e.g., "gaming")
    changes: Changes              # What to change
    validate: ValidateSpec?       # Optional validation targets
    rationale: List[str]?         # Why these changes?

class Changes(BaseModel):
    # Sysctl parameters
    sysctl: Dict[str, str]?       # e.g., {"net.ipv4.tcp_congestion_control": "bbr"}
    
    # Traffic Control
    qdisc: Qdisc?                 # Queue discipline config
    shaper: Shaper?               # Bandwidth shaping
    netem: Netem?                 # Network emulation (delay, loss)
    htb_classes: List[HTBClass]?  # HTB class configuration
    
    # Firewall/Security
    dscp: List[DSCPRule]?         # QoS marking rules
    connection_limits: List[ConnectionLimit]?
    rate_limits: List[RateLimit]?
    connection_tracking: ConnectionTracking?
    nat_rules: List[NATRule]?
    
    # NIC settings
    offloads: Offloads?           # GRO, GSO, TSO, LRO
    mtu: int?                     # MTU size
```

**Example ParameterPlan JSON**:

```json
{
  "iface": "eth0",
  "profile": "gaming",
  "changes": {
    "sysctl": {
      "net.ipv4.tcp_congestion_control": "bbr",
      "net.ipv4.tcp_low_latency": "1",
      "net.core.rmem_max": "16777216"
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
  },
  "rationale": [
    "Optimize for low-latency gaming",
    "Protect SSH from brute force"
  ]
}
```

### 3.2 RenderedPlan (Concrete Commands)

After planning, we get executable commands:

```python
class RenderedPlan(BaseModel):
    sysctl_cmds: List[str]        # ["sysctl -w net.ipv4.tcp_congestion_control=bbr", ...]
    tc_script: str                # Multi-line tc commands
    nft_script: str               # nftables script
    ethtool_cmds: List[str]       # ["ethtool -K eth0 gro on", ...]
    ip_link_cmds: List[str]       # ["ip link set dev eth0 mtu 1500"]
```

**Example RenderedPlan**:

```json
{
  "sysctl_cmds": [
    "sysctl -w net.ipv4.tcp_congestion_control=bbr",
    "sysctl -w net.ipv4.tcp_low_latency=1",
    "sysctl -w net.core.rmem_max=16777216"
  ],
  "tc_script": "# Clear existing qdisc on eth0\ntc qdisc del dev eth0 root 2>/dev/null || true\n\n# Setup FQ qdisc on eth0\ntc qdisc add dev eth0 root fq",
  "nft_script": "#!/usr/sbin/nft -f\n\ntable inet filter {\n  chain input {\n    type filter hook input priority 0; policy accept;\n    tcp dport 22 ct state new add @connlimit_{ip saddr} { ip saddr ct count over 5 } drop\n  }\n}",
  "ethtool_cmds": [],
  "ip_link_cmds": []
}
```

### 3.3 ValidationResult

After validation:

```python
class ValidationResult(BaseModel):
    ok: bool                      # Did validation pass?
    issues: List[ValidationIssue] # Any problems found?
    normalized_plan: ParameterPlan? # Cleaned/normalized version
```

### 3.4 ChangeReport (Execution Result)

After applying changes:

```python
class ChangeReport(BaseModel):
    applied: bool                 # Were changes applied?
    dry_run: bool                 # Was this a dry run?
    commands_preview: dict        # What was attempted
    errors: List[str]             # Any errors?
    checkpoint_id: str?           # Checkpoint for rollback
    notes: List[str]              # Execution log
```

---

## 4. The Planning Pipeline 🔄

### Step-by-Step Flow

```
User Request → Validation → Planning → Rendering → Execution → Result
```

### 4.1 Validation (`server/tools/validator.py`)

**Function**: `validate_change_plan(parameter_plan: dict) -> dict`

**What it does**:
1. Schema validation (Pydantic)
2. Policy rule checking
3. Limit enforcement
4. Compatibility checks

**Example**:

```python
# Input
plan = {
    "iface": "eth0",
    "profile": "gaming",
    "changes": {
        "sysctl": {
            "net.core.rmem_max": "999999999999"  # TOO LARGE!
        }
    }
}

# Output
{
    "ok": false,
    "issues": [
        {
            "path": "changes.sysctl.net.core.rmem_max",
            "message": "Value exceeds maximum allowed: 268435456",
            "severity": "error"
        }
    ]
}
```

### 4.2 Planning (`server/tools/planner.py`)

**Function**: `render_change_plan(plan: dict) -> dict`

**What it does**: Converts high-level parameters to concrete commands

#### The Magic of Rendering

Let's trace how a single change flows through the planner:

**Input (ParameterPlan)**:
```python
{
    "iface": "eth0",
    "changes": {
        "sysctl": {
            "net.ipv4.tcp_congestion_control": "bbr"
        }
    }
}
```

**Planner Processing**:

```python
def render_change_plan(plan: dict) -> dict:
    param_plan = ParameterPlan(**plan)  # Parse & validate
    rendered = RenderedPlan()
    
    # Step 1: Render sysctl
    if param_plan.changes.sysctl:
        rendered.sysctl_cmds = _render_sysctl(param_plan.changes.sysctl)
    
    # Step 2: Render tc
    if param_plan.changes.qdisc or param_plan.changes.netem:
        rendered.tc_script = _render_tc(...)
    
    # Step 3: Render nftables
    if param_plan.changes.connection_limits:
        rendered.nft_script = _render_nft(...)
    
    return rendered.model_dump()
```

**Output (RenderedPlan)**:
```python
{
    "sysctl_cmds": [
        "sysctl -w net.ipv4.tcp_congestion_control=bbr"
    ],
    "tc_script": "",
    "nft_script": "",
    "ethtool_cmds": [],
    "ip_link_cmds": []
}
```

### 4.3 Detailed Rendering Functions

#### `_render_sysctl(sysctl_set)`

Simple: key-value pairs → commands

```python
def _render_sysctl(sysctl_set) -> list:
    commands = []
    for key, value in sysctl_set.root.items():
        commands.append(f"sysctl -w {key}={value}")
    return commands
```

#### `_render_tc(iface, qdisc, shaper, netem, htb_classes)`

Complex: Multiple configurations → tc script

```python
def _render_tc(...):
    lines = []
    
    # Clear existing
    lines.append(f"tc qdisc del dev {iface} root 2>/dev/null || true")
    
    # Add qdisc
    if qdisc.type == "fq":
        lines.append(f"tc qdisc add dev {iface} root fq")
    
    # Add netem if specified
    if netem:
        netem_parts = []
        if netem.delay_ms:
            netem_parts.append(f"delay {netem.delay_ms}ms")
        if netem.loss_pct:
            netem_parts.append(f"loss {netem.loss_pct}%")
        lines.append(f"tc qdisc add dev {iface} parent ... netem {' '.join(netem_parts)}")
    
    return "\n".join(lines)
```

#### `_render_nft(iface, sections)`

Comprehensive: Multiple rule types → nftables script

```python
def _render_nft(iface, sections):
    lines = ["#!/usr/sbin/nft -f", ""]
    
    # Connection limits
    if has_connection_limits:
        lines.append("table inet filter {")
        lines.append("  chain input {")
        for limit in connection_limits:
            lines.append(f"    {limit.protocol} dport {limit.port} ct state new ...")
        lines.append("  }")
        lines.append("}")
    
    # DSCP marking
    if has_dscp:
        lines.append("table ip mangle {")
        # ... DSCP rules
        lines.append("}")
    
    return "\n".join(lines)
```

---

## 5. Execution & Safety ⚡

### The Apply Module (`server/tools/apply/apply.py`)

This is where commands actually run!

### 5.1 The Safety Flow

```
┌──────────────────────────────────────┐
│  1. Create Checkpoint (snapshot)     │
│     Save current system state        │
└────────────┬─────────────────────────┘
             │
             ↓
┌──────────────────────────────────────┐
│  2. Apply Commands Sequentially      │
│     - sysctl commands                │
│     - tc script                      │
│     - nftables script                │
│     - ethtool commands               │
│     - ip link commands               │
└────────────┬─────────────────────────┘
             │
             ├─ SUCCESS ──→ Return ChangeReport
             │
             └─ FAILURE ──→ Automatic Rollback
                            ↓
                   Restore from checkpoint
```

### 5.2 Apply Function Walkthrough

```python
def apply_rendered_plan(rendered_plan: dict, checkpoint_label: str = None):
    # Parse input
    plan = RenderedPlan(**rendered_plan)
    
    # SAFETY: Create checkpoint
    checkpoint_result = snapshot_checkpoint(checkpoint_label)
    checkpoint_id = checkpoint_result["checkpoint_id"]
    
    try:
        # Apply sysctl commands
        for cmd in plan.sysctl_cmds:
            result = run(["sysctl", "-w", cmd.split()[2]], timeout=10)
            if not result["ok"]:
                raise RuntimeError(f"sysctl failed: {result['stderr']}")
        
        # Apply tc script
        if plan.tc_script:
            for line in plan.tc_script.splitlines():
                if line and not line.startswith("#"):
                    result = run(line.split(), timeout=10)
                    if not result["ok"]:
                        raise RuntimeError(f"tc failed: {result['stderr']}")
        
        # Apply nftables
        if plan.nft_script:
            result = apply_nft.apply_nft_ruleset(plan.nft_script)
            if not result["ok"]:
                raise RuntimeError(f"nft failed: {result['stderr']}")
        
        # Success!
        return ChangeReport(applied=True, checkpoint_id=checkpoint_id, ...)
    
    except Exception as e:
        # SAFETY: Automatic rollback
        rollback_to_checkpoint(checkpoint_id)
        return ChangeReport(applied=False, errors=[str(e)], ...)
```

### 5.3 Checkpoint System (`server/tools/apply/checkpoints.py`)

**How it works**:

```python
def snapshot_checkpoint(label: str = None):
    """Save current system state"""
    checkpoint_id = f"checkpoint_{timestamp}"
    
    state = {
        "sysctls": get_all_sysctl_values(),
        "tc_qdiscs": get_tc_qdiscs(),
        "nft_ruleset": get_nft_ruleset(),
        "timestamp": now(),
        "label": label
    }
    
    save_to_disk(checkpoint_id, state)
    return {"checkpoint_id": checkpoint_id}

def rollback_to_checkpoint(checkpoint_id: str):
    """Restore saved state"""
    state = load_from_disk(checkpoint_id)
    
    # Restore sysctls
    for key, value in state["sysctls"].items():
        run(["sysctl", "-w", f"{key}={value}"])
    
    # Restore tc
    apply_tc_state(state["tc_qdiscs"])
    
    # Restore nftables
    apply_nft_ruleset(state["nft_ruleset"])
```

### 5.4 Individual Apply Modules

#### `server/tools/apply/sysctl.py`

```python
def set_sysctl(kv: dict[str, str]) -> dict:
    """Apply sysctl settings"""
    for key, value in sorted(kv.items()):
        result = run(["sysctl", "-w", f"{key}={value}"], timeout=5)
        if not result["ok"]:
            return {"ok": False, "stderr": result["stderr"]}
    return {"ok": True}
```

#### `server/tools/apply/tc.py`

```python
def apply_tc_script(lines: list[str]) -> dict:
    """Execute tc commands line by line"""
    for line in lines:
        parts = line.split()
        result = run(parts, timeout=5)
        if not result["ok"]:
            return {"ok": False, "stderr": result["stderr"]}
    return {"ok": True}
```

#### `server/tools/apply/nft.py`

```python
def apply_nft_ruleset(ruleset: str) -> dict:
    """Apply nftables configuration atomically"""
    # Write to temp file
    with tempfile.NamedTemporaryFile("w") as f:
        f.write(ruleset)
        
        # Validate first
        check = run(["nft", "-c", "-f", f.name])
        if not check["ok"]:
            return {"ok": False, "stderr": check["stderr"]}
        
        # Apply
        apply = run(["nft", "-f", f.name])
        return apply
```

#### `server/tools/apply/iptables.py` (NEW!)

```python
def apply_connection_limits(limits: list[dict]) -> dict:
    """Apply connection limiting via nftables"""
    script = build_nft_connection_limit_script(limits)
    return apply_nft_ruleset(script)

def apply_rate_limits(limits: list[dict]) -> dict:
    """Apply rate limiting via nftables"""
    script = build_nft_rate_limit_script(limits)
    return apply_nft_ruleset(script)
```

---

## 6. MCP Server Integration 🌐

### What is MCP?

**Model Context Protocol** is a standard for LLMs to interact with external systems.

Think of it like an API, but specifically designed for AI agents.

### The MCP Server (`server/main.py`)

```python
from fastmcp import FastMCP

# Create MCP server
mcp = FastMCP("network-optimizer")

# Initialize policy registry
policy_registry = PolicyRegistry()
policy_registry.load_all()

# Register resources (data LLM can read)
register_resources(mcp, policy_registry)

# Register tools (functions LLM can call)
register_tools(mcp)
```

### 6.1 Resources (server/registry.py)

Resources are read-only data the LLM can query:

```python
@mcp.resource("policy://config_cards/list")
def get_policy_card_list() -> str:
    """List all available config cards"""
    cards = policy_registry.list()
    return json.dumps({
        "description": "Available network optimization configuration cards",
        "count": len(cards),
        "cards": cards
    })

@mcp.resource("policy://config_cards/{card_id}")
def get_policy_card(card_id: str) -> str:
    """Get details of a specific config card"""
    card = policy_registry.get(card_id)
    return json.dumps(card)
```

### 6.2 Tools (server/registry.py)

Tools are functions the LLM can call:

```python
@mcp.tool()
def render_change_plan_tool(plan: dict) -> dict:
    """
    Render a ParameterPlan into concrete commands.
    
    Args:
        plan: A ParameterPlan dictionary
    
    Returns:
        RenderedPlan with executable commands
    """
    return render_change_plan(plan)

@mcp.tool()
def validate_change_plan_tool(parameter_plan: dict) -> dict:
    """
    Validate a ParameterPlan against policies.
    
    Args:
        parameter_plan: A ParameterPlan to validate
    
    Returns:
        ValidationResult with ok status and issues
    """
    return validate_change_plan(parameter_plan)

@mcp.tool()
def apply_rendered_plan_tool(rendered_plan: dict, checkpoint_label: str = None) -> dict:
    """
    Apply commands with rollback protection.
    
    Args:
        rendered_plan: RenderedPlan to execute
        checkpoint_label: Optional label for checkpoint
    
    Returns:
        ChangeReport with status and errors
    """
    return apply_rendered_plan(rendered_plan, checkpoint_label)
```

### 6.3 Discovery Tools

```python
@mcp.tool()
def ip_info_tool() -> dict:
    """Get network interface information"""
    return discovery.get_ip_info()

@mcp.tool()
def tc_qdisc_show_tool() -> dict:
    """Show current traffic control configuration"""
    return discovery.get_tc_qdisc()

# ... 30+ discovery tools
```

---

## 7. Complete Flow Examples 🎯

### Example 1: Gaming Optimization (Simple)

**Step 1: LLM receives user request**
```
User: "Optimize my network for gaming on eth0"
```

**Step 2: LLM queries policy**
```python
# LLM calls resource
response = get_resource("policy://config_cards/list")
# Gets: List of all 29 config cards

# LLM calls resource for gaming profile
response = get_resource("policy://profiles/gaming")
# Gets: Gaming profile details with active_cards
```

**Step 3: LLM constructs ParameterPlan**
```python
plan = {
    "iface": "eth0",
    "profile": "gaming",
    "changes": {
        "sysctl": {
            "net.ipv4.tcp_congestion_control": "bbr",
            "net.ipv4.tcp_low_latency": "1",
            "net.core.rmem_max": "16777216",
            "net.core.wmem_max": "16777216"
        },
        "qdisc": {
            "type": "fq",
            "params": {}
        }
    },
    "rationale": [
        "BBR for low latency",
        "Small buffers to avoid bufferbloat",
        "FQ qdisc for consistent packet delivery"
    ]
}
```

**Step 4: LLM validates plan**
```python
# LLM calls tool
result = validate_change_plan_tool(plan)

# Returns:
{
    "ok": true,
    "issues": [],
    "normalized_plan": { ... }
}
```

**Step 5: LLM renders plan**
```python
# LLM calls tool
rendered = render_change_plan_tool(plan)

# Returns:
{
    "sysctl_cmds": [
        "sysctl -w net.ipv4.tcp_congestion_control=bbr",
        "sysctl -w net.ipv4.tcp_low_latency=1",
        "sysctl -w net.core.rmem_max=16777216",
        "sysctl -w net.core.wmem_max=16777216"
    ],
    "tc_script": "tc qdisc del dev eth0 root 2>/dev/null || true\ntc qdisc add dev eth0 root fq",
    "nft_script": "",
    "ethtool_cmds": [],
    "ip_link_cmds": []
}
```

**Step 6: LLM applies changes**
```python
# LLM calls tool
report = apply_rendered_plan_tool(rendered, checkpoint_label="gaming_opt")

# Returns:
{
    "applied": true,
    "dry_run": false,
    "errors": [],
    "checkpoint_id": "checkpoint_1699123456",
    "notes": [
        "Created checkpoint: checkpoint_1699123456",
        "Applying 4 sysctl commands",
        "✓ sysctl -w net.ipv4.tcp_congestion_control=bbr",
        "✓ sysctl -w net.ipv4.tcp_low_latency=1",
        "✓ sysctl -w net.core.rmem_max=16777216",
        "✓ sysctl -w net.core.wmem_max=16777216",
        "Applying tc script",
        "✓ tc script applied successfully",
        "All changes applied successfully (5 operations)"
    ]
}
```

### Example 2: Server Protection (Complex)

**User Request**: "Protect my web server from DDoS on eth0"

**LLM Analysis**: Server profile + connection limiting + rate limiting

**ParameterPlan**:
```python
{
    "iface": "eth0",
    "profile": "server",
    "changes": {
        "sysctl": {
            "net.ipv4.tcp_syncookies": "1",
            "net.ipv4.tcp_max_syn_backlog": "8192",
            "net.ipv4.tcp_fin_timeout": "15"
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
            "max_connections": 1000000
        }
    }
}
```

**Rendered Commands**:

```bash
# Sysctl
sysctl -w net.ipv4.tcp_syncookies=1
sysctl -w net.ipv4.tcp_max_syn_backlog=8192
sysctl -w net.ipv4.tcp_fin_timeout=15
sysctl -w net.netfilter.nf_conntrack_max=1000000

# Nftables
#!/usr/sbin/nft -f

table inet filter {
  chain input {
    type filter hook input priority 0; policy accept;
    
    # Connection limits
    tcp dport 80 ct state new add @connlimit_{ip saddr} { ip saddr ct count over 100 } drop
    tcp dport 443 ct state new add @connlimit_{ip saddr} { ip saddr ct count over 100 } drop
    
    # Rate limiting
    limit rate over 1000/second burst 50 packets drop
  }
}
```

---

## 8. Advanced Topics 🚀

### Command Allowlisting

**Location**: `server/config/allowlist.yaml`

Only allowlisted commands can execute:

```yaml
allowed_commands:
  - name: "sysctl"
    path: "/usr/sbin/sysctl"
    allowed_flags: ["-w", "-n", "-a"]
  
  - name: "tc"
    path: "/usr/sbin/tc"
    allowed_flags: ["qdisc", "class", "filter", "add", "del", "replace"]
```

### Shell Execution (`server/tools/util/shell.py`)

```python
def run(cmd: list[str], timeout: int = 30) -> dict:
    """
    Execute a command safely.
    
    Checks:
    1. Command is in allowlist
    2. Timeout to prevent hangs
    3. Captures stdout/stderr
    """
    # Validate against allowlist
    if not is_allowed(cmd[0]):
        return {"ok": False, "stderr": "Command not allowed"}
    
    try:
        result = subprocess.run(
            cmd,
            timeout=timeout,
            capture_output=True,
            text=True
        )
        return {
            "ok": result.returncode == 0,
            "code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "stderr": "Command timed out"}
```

### Policy Loader (`server/tools/util/policy_loader.py`)

```python
class PolicyRegistry:
    def __init__(self):
        self.config_cards = {}
        self.profiles = {}
        self.rules = {}
    
    def load_all(self):
        """Load all policy files from disk"""
        self.load_config_cards()
        self.load_profiles()
        self.load_rules()
    
    def get(self, card_id: str):
        """Get a specific config card"""
        return self.config_cards.get(card_id)
```

---

## Summary: The Complete Journey 🎉

```
1. USER REQUEST
   ↓
2. LLM QUERIES POLICY (Resources)
   - What cards exist?
   - What profiles match?
   ↓
3. LLM CONSTRUCTS PLAN (ParameterPlan)
   - High-level intent
   - Type-safe structure
   ↓
4. VALIDATION (validate_change_plan_tool)
   - Schema check
   - Policy rules
   - Limits enforcement
   ↓
5. RENDERING (render_change_plan_tool)
   - ParameterPlan → RenderedPlan
   - Abstract → Concrete commands
   ↓
6. EXECUTION (apply_rendered_plan_tool)
   - Create checkpoint
   - Execute commands
   - Rollback on failure
   ↓
7. RESULT (ChangeReport)
   - Success/failure status
   - Execution log
   - Checkpoint ID for rollback
```

---

## Key Files Reference 📁

```
mcp-net-optimizer/
├── server/
│   ├── main.py                    # MCP server entry point
│   ├── registry.py                # Tool & resource registration
│   ├── schema/
│   │   └── models.py              # Pydantic data models ⭐
│   └── tools/
│       ├── planner.py             # ParameterPlan → RenderedPlan ⭐
│       ├── validator.py           # Policy validation ⭐
│       ├── discovery.py           # System inspection tools
│       ├── apply/
│       │   ├── apply.py           # Main orchestrator ⭐
│       │   ├── sysctl.py          # Sysctl execution
│       │   ├── tc.py              # Traffic control execution
│       │   ├── nft.py             # Nftables execution
│       │   ├── iptables.py        # Connection/rate limiting (NEW!)
│       │   ├── offloads.py        # NIC offload settings
│       │   ├── mtu.py             # MTU configuration
│       │   └── checkpoints.py     # Snapshot/rollback ⭐
│       └── util/
│           ├── policy_loader.py   # Load YAML policies
│           ├── shell.py           # Safe command execution
│           └── resp.py            # Response formatting
└── policy/
    ├── config_cards/              # 29 config card definitions ⭐
    ├── profiles.yaml              # 5 profile definitions ⭐
    ├── rules.yaml                 # Validation rules
    ├── limits.yaml                # Value constraints
    └── validation_limits.yaml     # Limit enforcement
```

---

This is your complete guide! The system is elegant because it separates concerns:
- **Policy** (YAML) defines *what's possible*
- **Schema** (Pydantic) ensures *data validity*
- **Planner** translates *intent to commands*
- **Apply** executes *safely with rollback*
- **MCP** exposes *everything to AI agents*

You now understand the full architecture! 🎓
