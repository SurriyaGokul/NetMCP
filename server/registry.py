import json
from server.tools.planner import render_change_plan
from server.tools.validator import validate_change_plan
from server.tools.apply.apply import apply_rendered_plan
from server.tools.apply.checkpoints import (
    snapshot_checkpoint,
    rollback_to_checkpoint,
    list_checkpoints,
    delete_checkpoint
)
from server.tools import discovery as _disc
from server.tools.apply import (
    sysctl as _apply_sysctl,
    tc as _apply_tc,
    nft as _apply_nft,
    iptables as _apply_iptables
)
from server.tools.validation_metrics import run_full_benchmark
from server.tools.validation_engine import ValidationEngine
from server.tools.audit_log import get_audit_logger
from server.tools.util.shell import (
    check_sudo_access,
    request_sudo_access,
    extend_sudo_cache,
    is_sudo_configured
)


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
    
# Sudo/Privileges Management Tools
    
    @mcp.tool()
    def check_sudo_access_tool() -> dict:
        """
        Check if sudo (root) access is available for running privileged network commands.
        Returns whether passwordless sudo is configured or if credentials are cached.
        """
        return check_sudo_access()
    
    @mcp.tool()
    def request_sudo_access_tool(password: str = None) -> dict:
        """
        Request sudo access by authenticating with password.
        Once authenticated, credentials are cached for ~15 minutes.
        For permanent access, user should run ./setup_sudo.sh instead.
        
        Args:
            password: User's sudo password. Required for authentication.
        
        Returns:
            Success status and cache duration info.
        """
        return request_sudo_access(password)
    
    @mcp.tool()
    def extend_sudo_cache_tool() -> dict:
        """
        Extend the sudo credential cache to prevent timeout during long operations.
        Call this periodically (every 10-14 minutes) during extended sessions.
        """
        return extend_sudo_cache()
    
    @mcp.tool()
    def get_sudo_setup_instructions_tool() -> dict:
        """
        Get instructions for setting up permanent passwordless sudo access.
        This is the recommended approach for regular use.
        """
        return {
            "instructions": [
                "For permanent passwordless sudo access, run the setup script:",
                "",
                "  ./setup_sudo.sh",
                "",
                "This will configure your system to allow the MCP server to run",
                "network configuration commands (sysctl, tc, nft, etc.) without",
                "requiring a password each time.",
                "",
                "The script only grants access to specific network tools, not full root."
            ],
            "alternative": "Or use request_sudo_access_tool with your password for temporary access (~15 min)",
            "is_configured": is_sudo_configured()
        }

# Core Plan Tools
    
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
        from server.tools.validation_metrics import quick_latency_test
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
        from server.tools.validation_engine import ValidationEngine
        
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

