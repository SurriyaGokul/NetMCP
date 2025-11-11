from __future__ import annotations
from typing import List, Dict, Optional, Literal
from pydantic import BaseModel, Field, conint, confloat, constr, RootModel

NonEmptyStr = constr(strip_whitespace=True, min_length=1)
Min3Str = constr(min_length=3)

class ValidateTargets(BaseModel):
    ping: Optional[NonEmptyStr] = None
    iperf: Optional[NonEmptyStr] = None

class ValidateObjectives(BaseModel):
    latency_p95_ms: Optional[confloat(gt=0, le=1000)] = None
    jitter_ms: Optional[confloat(ge=0, le=500)] = None
    loss_pct: Optional[confloat(ge=0, le=100)] = None
    throughput_mbps: Optional[confloat(gt=0)] = None

class ValidateSpec(BaseModel):
    targets: Optional[ValidateTargets] = None
    objectives: Optional[ValidateObjectives] = None

class Qdisc(BaseModel):
    type: Literal["cake", "fq_codel", "htb", "fq", "pfifo_fast"]
    params: Dict[str, object] = Field(default_factory=dict) 

class Shaper(BaseModel):
    ingress_mbit: Optional[conint(gt=0, le=100000)] = None
    egress_mbit: Optional[conint(gt=0, le=100000)] = None
    ceil_mbit: Optional[conint(gt=0, le=100000)] = None

class Netem(BaseModel):
    """Network emulation parameters for tc netem"""
    delay_ms: Optional[conint(ge=0, le=10000)] = None
    delay_jitter_ms: Optional[conint(ge=0, le=1000)] = None
    loss_pct: Optional[confloat(ge=0, le=100)] = None
    duplicate_pct: Optional[confloat(ge=0, le=100)] = None
    corrupt_pct: Optional[confloat(ge=0, le=100)] = None
    reorder_pct: Optional[confloat(ge=0, le=100)] = None

class HTBClass(BaseModel):
    """HTB class configuration"""
    classid: str  # e.g., "1:10"
    rate_mbit: conint(gt=0, le=100000)
    ceil_mbit: Optional[conint(gt=0, le=100000)] = None
    priority: Optional[conint(ge=0, le=7)] = None
    burst: Optional[str] = None  # e.g., "15k"

class SysctlSet(RootModel):
    root: Dict[str, str]

class DSCPMatch(BaseModel):
    proto: Optional[Literal["tcp", "udp"]] = None
    sports: Optional[List[conint(gt=0, lt=65536)]] = None
    dports: Optional[List[conint(gt=0, lt=65536)]] = None
    src: Optional[str] = None   # cidr string
    dst: Optional[str] = None

class DSCPRule(BaseModel):
    match: DSCPMatch
    dscp: Literal["EF", "CS6", "CS5", "CS4", "AF41", "AF42", "AF43"]

class ConnectionLimit(BaseModel):
    """iptables/nftables connection limiting"""
    protocol: Literal["tcp", "udp"]
    port: conint(gt=0, lt=65536)
    limit: conint(gt=0, le=10000)
    mask: Optional[conint(ge=0, le=32)] = 32  # CIDR mask for subnet limiting

class RateLimit(BaseModel):
    """iptables/nftables rate limiting"""
    rate: str  # e.g., "150/second", "1000/minute"
    burst: Optional[conint(gt=0, le=1000)] = None

class ConnectionTracking(BaseModel):
    """Connection tracking configuration"""
    max_connections: Optional[conint(gt=0, le=10000000)] = None
    tcp_timeout_established: Optional[conint(gt=0, le=432000)] = None  # seconds
    tcp_timeout_close_wait: Optional[conint(gt=0, le=3600)] = None

class NATRule(BaseModel):
    """NAT rule configuration"""
    type: Literal["snat", "dnat", "masquerade"]
    iface: Optional[str] = None
    to_addr: Optional[str] = None  # for SNAT/DNAT
    to_port: Optional[conint(gt=0, lt=65536)] = None

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
    iface: NonEmptyStr
    profile: NonEmptyStr
    changes: Changes
    validation: Optional[ValidateSpec] = None
    rationale: Optional[NonEmptyStr] = None

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

