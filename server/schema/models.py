from __future__ import annotations
from typing import List, Dict, Optional, Literal
from pydantic import BaseModel, Field, conint, confloat, constr

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
    type: Literal["cake", "fq_codel", "htb"]
    params: Dict[str, object] = Field(default_factory=dict) 

class Shaper(BaseModel):
    ingress_mbit: Optional[conint(gt=0, le=100000)] = None
    egress_mbit: Optional[conint(gt=0, le=100000)] = None
    ceil_mbit: Optional[conint(gt=0, le=100000)] = None

class Offloads(BaseModel):
    gro: Optional[bool] = None
    gso: Optional[bool] = None
    tso: Optional[bool] = None
    lro: Optional[bool] = None

class SysctlSet(BaseModel):
    __root__: Dict[str, str]

class DSCPMatch(BaseModel):
    proto: Optional[Literal["tcp", "udp"]] = None
    sports: Optional[List[conint(gt=0, lt=65536)]] = None
    dports: Optional[List[conint(gt=0, lt=65536)]] = None
    src: Optional[str] = None   # cidr string
    dst: Optional[str] = None

class DSCPRule(BaseModel):
    match: DSCPMatch
    dscp: Literal["EF", "CS6", "CS5", "CS4", "AF41", "AF42", "AF43"]

class Changes(BaseModel):
    qdisc: Optional[Qdisc] = None
    shaper: Optional[Shaper] = None
    sysctl: Optional[SysctlSet] = None
    offloads: Optional[Offloads] = None
    dscp: Optional[List[DSCPRule]] = None
    mtu: Optional[conint(ge=576, le=9000)] = None  # IPv4 safe min through jumbo

class ParameterPlan(BaseModel):
    iface: NonEmptyStr
    profile: NonEmptyStr
    changes: Changes
    validate: Optional[ValidateSpec] = None
    rationale: Optional[List[Min3Str]] = None

class RenderedPlan(BaseModel):
    sysctl_cmds: List[str] = Field(default_factory=list)      # ["sysctl -w net.ipv4.tcp_congestion_control=bbr", ...]
    tc_script: str = ""                                       # full multiline `tc` script
    nft_script: str = ""                                      # full multiline `nft -f` script (or empty if unused)
    ethtool_cmds: List[str] = Field(default_factory=list)     # ["ethtool -K eth0 gro off", ...]
    ip_link_cmds: List[str] = Field(default_factory=list)     # ["ip link set dev eth0 mtu 1500"]

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
