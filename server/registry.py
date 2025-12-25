import json
from .tools.planner import render_change_plan
from .tools.validator import validate_change_plan
from .tools.apply.apply import apply_rendered_plan
from .tools.apply.checkpoints import (
    snapshot_checkpoint,
    rollback_to_checkpoint,
    list_checkpoints,
    delete_checkpoint
)
from .tools import discovery as _disc
from .tools.apply import (
    sysctl as _apply_sysctl,
    tc as _apply_tc,
    nft as _apply_nft,
    iptables as _apply_iptables
)
from .tools.validation_metrics import run_full_benchmark
from .tools.validation_engine import ValidationEngine
from .tools.audit_log import get_audit_logger


def register_resources(mcp, policy_registry):
    @mcp.resource("policy://config_cards/list")
    def get_policy_card_list() -> str:
        cards = policy_registry.list()
        return json.dumps({
            "description": "Available network optimization configuration cards",
            "count": len(cards),
            "cards": cards
        }, indent=2)
    
    @mcp.resource("policy://config_cards/{card_id}")
    def get_policy_card(card_id: str) -> str:
        card = policy_registry.get(card_id)
        if not card:
            return json.dumps({"error": f"Configuration card '{card_id}' not found"})
        return json.dumps(card, indent=2)


def register_tools(mcp):
    @mcp.tool()
    def render_change_plan_tool(plan: dict) -> dict:
        return render_change_plan(plan)
    
    @mcp.tool()
    def validate_change_plan_tool(parameter_plan: dict) -> dict:
        return validate_change_plan(parameter_plan)
    
    @mcp.tool()
    def apply_rendered_plan_tool(rendered_plan: dict, checkpoint_label: str = None) -> dict:
        return apply_rendered_plan(rendered_plan, checkpoint_label)

    @mcp.tool()
    def snapshot_checkpoint_tool(label: str = None) -> dict:
        return snapshot_checkpoint(label)
    
    @mcp.tool()
    def rollback_to_checkpoint_tool(checkpoint_id: str) -> dict:
        return rollback_to_checkpoint(checkpoint_id)
    
    @mcp.tool()
    def list_checkpoints_tool() -> dict:
        return list_checkpoints()
    
    @mcp.tool()
    def delete_checkpoint_tool(checkpoint_id: str) -> dict:
        return delete_checkpoint(checkpoint_id)
    
    @mcp.tool()
    def test_network_performance_tool(profile: str = "gaming") -> dict:
        return run_full_benchmark(profile)
    
    @mcp.tool()
    def quick_latency_test_tool() -> dict:
        from .tools.validation_metrics import quick_latency_test
        return quick_latency_test()
    
    @mcp.tool()
    def validate_configuration_changes_tool(
        before_results: dict,
        after_results: dict,
        profile: str = "gaming"
    ) -> dict:
        return ValidationEngine.compare_benchmarks(before_results, after_results, profile)
    
    @mcp.tool()
    def auto_validate_and_rollback_tool(
        checkpoint_id: str,
        before_results: dict,
        after_results: dict,
        profile: str = "gaming",
        auto_rollback: bool = True
    ) -> dict:
        from .tools.validation_engine import ValidationEngine
        
        validation = ValidationEngine.compare_benchmarks(before_results, after_results, profile)
        
        action_taken = "NO_ACTION"
        result = {"validation": validation}
        
        if validation["decision"] == "ROLLBACK" and auto_rollback:
            rollback_result = rollback_to_checkpoint(checkpoint_id)
            result["rollback_result"] = rollback_result
            if rollback_result.get("ok"):
                action_taken = "ROLLED_BACK"
                result["message"] = "Configuration rolled back due to performance degradation"
            else:
                action_taken = "ROLLBACK_FAILED"
                result["message"] = "Rollback attempted but failed - manual intervention required"
        elif validation["decision"] == "KEEP":
            action_taken = "KEPT"
            result["message"] = "Configuration changes kept - performance improved"
        elif validation["decision"] == "UNCERTAIN":
            action_taken = "KEPT"
            result["message"] = "Configuration kept but results uncertain - manual review recommended"
        
        result["action_taken"] = action_taken
        return result
    
# Discovery Tools
    
    @mcp.tool()
    def ip_info() -> dict:
        return _disc.ip_info()
    
    @mcp.tool()
    def eth_info(iface: str = "eth0") -> dict:
        return _disc.eth_info(iface)
    
    @mcp.tool()
    def hostname_ips() -> dict:
        return _disc.hostname_ips()
    
    @mcp.tool()
    def hostnamectl() -> dict:
        return _disc.hostnamectl()
    
    @mcp.tool()
    def nmcli_status() -> dict:
        return _disc.nmcli_status()
    
    @mcp.tool()
    def iwconfig(iface: str = "wlan0") -> dict:
        return _disc.iwconfig(iface)
    
    @mcp.tool()
    def iwlist_scan(iface: str = "wlan0", subcmd: str = "scan") -> dict:
        return _disc.iwlist_scan(iface, subcmd)
    
    @mcp.tool()
    def arp_table() -> dict:
        return _disc.arp_table()
    
    @mcp.tool()
    def ip_neigh() -> dict:
        return _disc.ip_neigh()
    
    @mcp.tool()
    def ip_route() -> dict:
        return _disc.ip_route()
    
    @mcp.tool()
    def resolvectl_status() -> dict:
        return _disc.resolvectl_status()
    
    @mcp.tool()
    def cat_resolv_conf() -> dict:
        return _disc.cat_resolv_conf()
    
    @mcp.tool()
    def dig(domain: str, dns: str | None = None) -> dict:
        return _disc.dig(domain, dns)
    
    @mcp.tool()
    def host(domain: str) -> dict:
        return _disc.host(domain)
    
    @mcp.tool()
    def nslookup(domain: str) -> dict:
        return _disc.nslookup(domain)
    
    @mcp.tool()
    def ping_host(address: str, count: int = 3) -> dict:
        return _disc.ping_host(address, count)
    
    @mcp.tool()
    def traceroute(domain: str) -> dict:
        return _disc.traceroute(domain)
    
    @mcp.tool()
    def tracepath(domain: str) -> dict:
        return _disc.tracepath(domain)
    
    @mcp.tool()
    def ss_summary(options: str = "tulwn") -> dict:
        return _disc.ss_summary(options)
    
    @mcp.tool()
    def tc_qdisc_show(iface: str) -> dict:
        return _disc.tc_qdisc_show(iface)
    
    @mcp.tool()
    def nft_list_ruleset() -> dict:
        return _disc.nft_list_ruleset()
    
    @mcp.tool()
    def iptables_list() -> dict:
        return _disc.iptables_list()
    
# Applying Tools
    
    @mcp.tool()
    def set_sysctl(kv: dict[str, str]) -> dict:
        return _apply_sysctl.set_sysctl(kv)
    
    @mcp.tool()
    def apply_tc_script(lines: list[str]) -> dict:
        return _apply_tc.apply_tc_script(lines)
    
    @mcp.tool()
    def apply_nft_ruleset(ruleset: str) -> dict:
        return _apply_nft.apply_nft_ruleset(ruleset)
    
# AUDIT LOGGING
    
    @mcp.tool()
    def get_audit_log_tool(limit: int = 50) -> dict:
        logger = get_audit_logger()
        entries = logger.get_recent_entries(limit)
        
        return {
            "ok": True,
            "count": len(entries),
            "entries": entries
        }
    
    @mcp.tool()
    def search_audit_log_tool(
        action: str = None,
        checkpoint_id: str = None,
        start_date: str = None,
        end_date: str = None
    ) -> dict:
        logger = get_audit_logger()
        entries = logger.search_entries(action, checkpoint_id, start_date, end_date)
        
        return {
            "ok": True,
            "count": len(entries),
            "filters": {
                "action": action,
                "checkpoint_id": checkpoint_id,
                "start_date": start_date,
                "end_date": end_date
            },
            "entries": entries
        }

