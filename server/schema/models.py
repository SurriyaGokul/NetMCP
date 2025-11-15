from __future__ import annotations
from typing import List, Dict, Optional, Literal, Union
from pydantic import BaseModel, Field, RootModel

class ValidateTargets(BaseModel):
    ping: Optional[str] = None
    iperf: Optional[str] = None

class ValidateObjectives(BaseModel):
    latency_p95_ms: Optional[float] = None
    jitter_ms: Optional[float] = None
    loss_pct: Optional[float] = None
    throughput_mbps: Optional[float] = None

class ValidateSpec(BaseModel):
    targets: Optional[ValidateTargets] = None
    objectives: Optional[ValidateObjectives] = None
    
class Qdisc(BaseModel):
    type: str  # cake, fq_codel, htb, fq, pfifo_fast, or any valid qdisc
    params: Dict[str, object] = Field(default_factory=dict) 

class Shaper(BaseModel):
    ingress_mbit: Optional[int] = None
    egress_mbit: Optional[int] = None
    ceil_mbit: Optional[int] = None

class Netem(BaseModel):
    """Network emulation parameters for tc netem"""
    delay_ms: Optional[int] = None
    delay_jitter_ms: Optional[int] = None
    loss_pct: Optional[float] = None
    duplicate_pct: Optional[float] = None
    corrupt_pct: Optional[float] = None
    reorder_pct: Optional[float] = None

class HTBClass(BaseModel):
    """HTB class configuration"""
    classid: str  # e.g., "1:10"
    rate_mbit: int
    ceil_mbit: Optional[int] = None
    priority: Optional[int] = None
    burst: Optional[str] = None  # e.g., "15k"

class SysctlSet(RootModel):
    root: Dict[str, Union[str, int, float]]

class DSCPMatch(BaseModel):
    proto: Optional[str] = None  # tcp, udp, or any protocol
    sports: Optional[List[int]] = None
    dports: Optional[List[int]] = None
    src: Optional[str] = None   # cidr string
    dst: Optional[str] = None

class DSCPRule(BaseModel):
    match: DSCPMatch
    dscp: str  # EF, CS6, CS5, CS4, AF41, AF42, AF43, or any valid DSCP

class ConnectionLimit(BaseModel):
    """iptables/nftables connection limiting"""
    protocol: str  # tcp, udp, or any protocol
    port: int
    limit: int
    mask: Optional[int] = 32  # CIDR mask for subnet limiting

class RateLimit(BaseModel):
    """iptables/nftables rate limiting"""
    rate: str  # e.g., "150/second", "1000/minute"
    burst: Optional[int] = None

class ConnectionTracking(BaseModel):
    """Connection tracking configuration"""
    max_connections: Optional[int] = None
    tcp_timeout_established: Optional[int] = None  # seconds
    tcp_timeout_close_wait: Optional[int] = None

class NATRule(BaseModel):
    """NAT rule configuration"""
    type: str  # snat, dnat, masquerade
    iface: Optional[str] = None
    to_addr: Optional[str] = None  # for SNAT/DNAT
    to_port: Optional[int] = None

class Changes(BaseModel):
    qdisc: Optional[Qdisc] = None
    shaper: Optional[Shaper] = None
    netem: Optional[Netem] = None
    htb_classes: Optional[List[HTBClass]] = None
    sysctl: Optional[SysctlSet] = None
    dscp: Optional[List[DSCPRule]] = None
    connection_limits: Optional[List[ConnectionLimit]] = None
    rate_limits: Optional[List[RateLimit]] = None
    connection_tracking: Optional[ConnectionTracking] = None
    nat_rules: Optional[List[NATRule]] = None

class ParameterPlan(BaseModel):
    model_config = {"populate_by_name": True}  # Pydantic v2: Allow both 'iface' and 'interface'
    
    iface: str = Field(..., alias='interface', description="Network interface name (e.g., 'eth0', 'wlan0')")
    profile: str = Field(..., description="Profile name from available profiles")
    changes: Changes = Field(..., description="Network configuration changes to apply")
    validation: Optional[ValidateSpec] = Field(None, description="Optional validation targets and objectives")
    rationale: Optional[str] = Field(None, description="Optional explanation for the changes")

class RenderedPlan(BaseModel):
    sysctl_cmds: List[str] = Field(default_factory=list)      # ["sysctl -w net.ipv4.tcp_congestion_control=bbr", ...]
    tc_script: str = ""                                       # full multiline `tc` script
    nft_script: str = ""                                      # full multiline `nft -f` script (or empty if unused)

class ChangeReport(BaseModel):
    applied: bool
    dry_run: bool
    commands_preview: Dict[str, object] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)
    checkpoint_id: Optional[str] = None
    notes: Optional[List[str]] = None

class ValidationIssue(BaseModel):
    path: str
    message: str
    severity: Literal["error", "warning"]

class ValidationResult(BaseModel):
    ok: bool
    issues: List[ValidationIssue] = Field(default_factory=list)
    normalized_plan: Optional[ParameterPlan] = None

PARAMETER_PLAN_SCHEMA = ParameterPlan.model_json_schema()
RENDERED_PLAN_SCHEMA = RenderedPlan.model_json_schema()
CHANGE_REPORT_SCHEMA = ChangeReport.model_json_schema()
VALIDATION_RESULT_SCHEMA = ValidationResult.model_json_schema()

