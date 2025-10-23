from pydantic import BaseModel
from typing import List, Optional,Dict, Any

class ParameterPlan(BaseModel):
    sysctl_params: Optional[Dict[str, Any]] = None
    tc_settings: Optional[List[Dict[str, Any]]] = None
    nft_rules: Optional[List[Dict[str, Any]]] = None
    ip_settings: Optional[List[Dict[str, Any]]] = None
    ethtool_settings: Optional[List[Dict[str, Any]]] = None

class RenderedPlan(BaseModel):
    sysctl_cmds: List[str]
    tc_script: str
    nft_script: str
    ip_link_cmds: List[str]
    ethtool_cmds: List[str]

class ChangeReport(BaseModel):
    applied: bool
    dry_run: bool
    commands_preview: Dict[str, Any]
    errors: List[str]
   
class ValidationResult(BaseModel):
    # TODO: Hari you have to implement.
    is_valid: bool