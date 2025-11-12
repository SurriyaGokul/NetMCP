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


def register_resources(mcp, policy_registry):
    """
    Register MCP resources for accessing policy configuration cards.
    
    Resources provide read-only access to configuration metadata and documentation.
    """
    
    @mcp.resource("policy://config_cards/list")
    def get_policy_card_list() -> str:
        """List all available network optimization configuration cards."""
        cards = policy_registry.list()
        return json.dumps({
            "description": "Available network optimization configuration cards",
            "count": len(cards),
            "cards": cards
        }, indent=2)
    
    @mcp.resource("policy://config_cards/{card_id}")
    def get_policy_card(card_id: str) -> str:
        """Get detailed information about a specific configuration card."""
        card = policy_registry.get(card_id)
        if not card:
            return json.dumps({"error": f"Configuration card '{card_id}' not found"})
        return json.dumps(card, indent=2)


def register_tools(mcp):
    """
    Register all MCP tools with the FastMCP server.
    
    This function creates the complete tool API surface for network optimization,
    organized into six functional categories for clear navigation and usage.
    """
    
    # ========================================================================
    # CORE WORKFLOW TOOLS
    # ========================================================================
    
    @mcp.tool()
    def render_change_plan_tool(plan: dict) -> dict:
        """
        Render a ParameterPlan into executable commands and scripts.
        
        Translates high-level optimization goals into concrete system commands
        without executing them. This is a pure transformation with no side effects.
        
        Args:
            plan: ParameterPlan with interface, profile, changes, and rationale
            
        Returns:
            RenderedPlan containing:
            - sysctl_cmds: List of kernel parameter commands
            - tc_script: Traffic control configuration script
            - nft_script: Complete nftables ruleset
        """
        return render_change_plan(plan)
    
    @mcp.tool()
    def validate_change_plan_tool(parameter_plan: dict) -> dict:
        """
        Validate a ParameterPlan against schemas and policy constraints.
        
        Performs comprehensive multi-layer validation including schema validation,
        policy limit enforcement, interface existence checks, and configuration
        card parameter verification.
        
        Args:
            parameter_plan: ParameterPlan to validate
            
        Returns:
            ValidationResult containing:
            - ok: True if validation passed
            - issues: List of error messages (empty if ok=True)
            - normalized_plan: Cleaned and validated plan
        """
        return validate_change_plan(parameter_plan)
    
    @mcp.tool()
    def apply_rendered_plan_tool(rendered_plan: dict, checkpoint_label: str = None) -> dict:
        """
        Apply a RenderedPlan atomically with automatic rollback on failure.
        
        Safely executes network configuration changes with comprehensive safety
        features including command allowlisting, automatic checkpointing, and
        rollback on any error.
        
        Execution sequence:
        1. Create checkpoint snapshot
        2. Execute sysctl commands
        3. Execute traffic control script
        4. Execute nftables script
        5. Rollback automatically if any step fails
        
        Args:
            rendered_plan: RenderedPlan from render_change_plan_tool()
            checkpoint_label: Optional descriptive label for checkpoint
            
        Returns:
            ChangeReport containing:
            - applied: True if all commands succeeded
            - errors: List of error messages
            - checkpoint_id: ID for manual rollback
            - notes: Detailed execution log
        """
        return apply_rendered_plan(rendered_plan, checkpoint_label)
    
    # ========================================================================
    # CHECKPOINT MANAGEMENT
    # ========================================================================
    
    @mcp.tool()
    def snapshot_checkpoint_tool(label: str = None) -> dict:
        """
        Create a checkpoint of current network configuration state.
        
        Captures sysctl parameters, traffic control configuration, and
        nftables rules for later restoration.
        
        Args:
            label: Optional descriptive label
            
        Returns:
            dict with checkpoint_id and timestamp
        """
        return snapshot_checkpoint(label)
    
    @mcp.tool()
    def rollback_to_checkpoint_tool(checkpoint_id: str) -> dict:
        """
        Restore network configuration from a checkpoint.
        
        Reverts all network settings to the captured state. Use
        list_checkpoints_tool() to see available checkpoints.
        
        Args:
            checkpoint_id: Checkpoint ID to restore
            
        Returns:
            dict with ok status, restored settings, and notes
        """
        return rollback_to_checkpoint(checkpoint_id)
    
    @mcp.tool()
    def list_checkpoints_tool() -> dict:
        """
        List all available checkpoints.
        
        Returns:
            dict with checkpoint metadata (ID, label, timestamp)
        """
        return list_checkpoints()
    
    @mcp.tool()
    def delete_checkpoint_tool(checkpoint_id: str) -> dict:
        """
        Delete a specific checkpoint to free storage.
        
        Args:
            checkpoint_id: Checkpoint ID to delete
            
        Returns:
            dict with ok status
        """
        return delete_checkpoint(checkpoint_id)
    
    # ========================================================================
    # PERFORMANCE TESTING & VALIDATION
    # ========================================================================
    
    @mcp.tool()
    def test_network_performance_tool(profile: str = "gaming") -> dict:
        """
        Run comprehensive network performance benchmarks.
        
        Executes profile-specific tests to measure latency, jitter, packet loss,
        DNS resolution, and connection speeds. Use before and after configuration
        changes to measure impact.
        
        Profiles:
        - gaming: Latency and jitter focused (20-30 pings)
        - throughput: Bandwidth tests with iperf3
        - balanced: Mixed tests with moderate samples
        - low-latency: Ultra-strict latency testing
        
        Args:
            profile: Test profile to use
            
        Returns:
            dict with latency, jitter, packet_loss, dns_resolution,
            connection_time, and optional throughput metrics
        """
        from .tools.validation_metrics import run_full_benchmark
        return run_full_benchmark(profile)
    
    @mcp.tool()
    def quick_latency_test_tool() -> dict:
        """
        Quick 10-ping latency test for rapid comparisons.
        
        Useful during interactive optimization sessions for fast before/after
        measurements.
        
        Returns:
            dict with avg_ms, jitter_ms, packet_loss_percent
        """
        from .tools.validation_metrics import quick_latency_test
        return quick_latency_test()
    
    @mcp.tool()
    def validate_configuration_changes_tool(
        before_results: dict,
        after_results: dict,
        profile: str = "gaming"
    ) -> dict:
        """
        Compare before/after performance and recommend action.
        
        Analyzes benchmark results and provides KEEP, ROLLBACK, or UNCERTAIN
        decision based on profile-specific criteria and weighted metrics.
        
        Decision criteria by profile:
        - gaming: Latency 40%, jitter 30%, packet loss 20%, connection 10%
        - throughput: Bandwidth 50%, stability 20%, retransmits 20%, connection 10%
        - balanced: Equal weight to latency and throughput
        - low-latency: Ultra-strict on latency (any increase triggers ROLLBACK)
        
        Args:
            before_results: Benchmark before changes
            after_results: Benchmark after changes
            profile: Validation profile
            
        Returns:
            dict with decision, score (0-100), summary, reasons, and
            detailed metrics comparison
        """
        from .tools.validation_engine import ValidationEngine
        return ValidationEngine.compare_benchmarks(before_results, after_results, profile)
    
    @mcp.tool()
    def auto_validate_and_rollback_tool(
        checkpoint_id: str,
        before_results: dict,
        after_results: dict,
        profile: str = "gaming",
        auto_rollback: bool = True
    ) -> dict:
        """
        Automated validation with conditional rollback.
        
        Combines performance validation with automatic rollback for
        streamlined testing workflows. If performance degrades, automatically
        reverts to checkpoint.
        
        Args:
            checkpoint_id: Checkpoint to rollback to if needed
            before_results: Benchmark before changes
            after_results: Benchmark after changes
            profile: Validation profile
            auto_rollback: Enable automatic rollback on degradation
            
        Returns:
            dict with validation results, action_taken (KEPT/ROLLED_BACK/NO_ACTION),
            and optional rollback_result
        """
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
    
    # ========================================================================
    # NETWORK DISCOVERY TOOLS
    # ========================================================================
    
    @mcp.tool()
    def ip_info() -> dict:
        """Get network interfaces and IP addresses."""
        return _disc.ip_info()
    
    @mcp.tool()
    def eth_info(iface: str = "eth0") -> dict:
        """Get interface hardware capabilities and driver information."""
        return _disc.eth_info(iface)
    
    @mcp.tool()
    def hostname_ips() -> dict:
        """Get all IP addresses for local hostname."""
        return _disc.hostname_ips()
    
    @mcp.tool()
    def hostnamectl() -> dict:
        """Get system hostname and OS metadata."""
        return _disc.hostnamectl()
    
    @mcp.tool()
    def nmcli_status() -> dict:
        """Get NetworkManager device connection status."""
        return _disc.nmcli_status()
    
    @mcp.tool()
    def iwconfig(iface: str = "wlan0") -> dict:
        """Get wireless interface parameters."""
        return _disc.iwconfig(iface)
    
    @mcp.tool()
    def iwlist_scan(iface: str = "wlan0", subcmd: str = "scan") -> dict:
        """Scan for available wireless networks."""
        return _disc.iwlist_scan(iface, subcmd)
    
    @mcp.tool()
    def arp_table() -> dict:
        """Get ARP table with IP-to-MAC mappings."""
        return _disc.arp_table()
    
    @mcp.tool()
    def ip_neigh() -> dict:
        """Get neighbor cache for ARP and NDP."""
        return _disc.ip_neigh()
    
    @mcp.tool()
    def ip_route() -> dict:
        """Get routing table."""
        return _disc.ip_route()
    
    @mcp.tool()
    def resolvectl_status() -> dict:
        """Get DNS resolver configuration."""
        return _disc.resolvectl_status()
    
    @mcp.tool()
    def cat_resolv_conf() -> dict:
        """Get /etc/resolv.conf contents."""
        return _disc.cat_resolv_conf()
    
    @mcp.tool()
    def dig(domain: str, dns: str | None = None) -> dict:
        """Perform DNS query with dig."""
        return _disc.dig(domain, dns)
    
    @mcp.tool()
    def host(domain: str) -> dict:
        """Perform simple DNS lookup."""
        return _disc.host(domain)
    
    @mcp.tool()
    def nslookup(domain: str) -> dict:
        """Perform legacy DNS query."""
        return _disc.nslookup(domain)
    
    @mcp.tool()
    def ping_host(address: str, count: int = 3) -> dict:
        """Test ICMP reachability and latency."""
        return _disc.ping_host(address, count)
    
    @mcp.tool()
    def traceroute(domain: str) -> dict:
        """Trace network path to destination."""
        return _disc.traceroute(domain)
    
    @mcp.tool()
    def tracepath(domain: str) -> dict:
        """Trace path without root privileges."""
        return _disc.tracepath(domain)
    
    @mcp.tool()
    def ss_summary(options: str = "tulwn") -> dict:
        """Get socket statistics and active connections."""
        return _disc.ss_summary(options)
    
    @mcp.tool()
    def tc_qdisc_show(iface: str) -> dict:
        """Get traffic control qdisc configuration and stats."""
        return _disc.tc_qdisc_show(iface)
    
    @mcp.tool()
    def nft_list_ruleset() -> dict:
        """Get nftables firewall ruleset."""
        return _disc.nft_list_ruleset()
    
    @mcp.tool()
    def iptables_list() -> dict:
        """Get iptables firewall rules."""
        return _disc.iptables_list()
    
    # ========================================================================
    # DIRECT APPLY TOOLS
    # ========================================================================
    
    @mcp.tool()
    def set_sysctl(kv: dict[str, str]) -> dict:
        """
        Apply kernel parameters directly via sysctl.
        
        Executes sysctl commands in sorted order. Stops on first error.
        For production use, prefer apply_rendered_plan_tool() which includes
        validation and automatic rollback.
        
        Args:
            kv: Dictionary of parameter names to values
            
        Returns:
            dict with ok status, exit_code, stdout, stderr
        """
        return _apply_sysctl.set_sysctl(kv)
    
    @mcp.tool()
    def apply_tc_script(lines: list[str]) -> dict:
        """
        Execute traffic control commands directly.
        
        Runs tc commands sequentially without validation or rollback.
        For production use, prefer apply_rendered_plan_tool().
        
        Args:
            lines: List of tc command strings
            
        Returns:
            dict with ok status, exit_code, stdout, stderr
        """
        return _apply_tc.apply_tc_script(lines)
    
    @mcp.tool()
    def apply_nft_ruleset(ruleset: str) -> dict:
        """
        Apply a complete nftables ruleset directly.
        
        Loads the ruleset via 'nft -f' without validation or rollback.
        For production use, prefer apply_rendered_plan_tool().
        
        Args:
            ruleset: Complete nftables configuration
            
        Returns:
            dict with ok status, exit_code, stdout, stderr
        """
        return _apply_nft.apply_nft_ruleset(ruleset)
    
    # ========================================================================
    # AUDIT LOGGING
    # ========================================================================
    
    @mcp.tool()
    def get_audit_log_tool(limit: int = 50) -> dict:
        """
        Get recent audit log entries.
        
        Returns history of all configuration changes, command executions,
        validations, and rollback operations with timestamps.
        
        Args:
            limit: Maximum number of recent entries (default: 50)
            
        Returns:
            dict with count and entries list
        """
        from .tools.audit_log import get_audit_logger
        
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
        """
        Search audit log entries by criteria.
        
        Filter by action type, checkpoint ID, or date range. All filters
        are optional and can be combined.
        
        Args:
            action: Filter by action type (apply_plan, validate_plan,
                   create_checkpoint, rollback, execute_command, validation_test)
            checkpoint_id: Filter by checkpoint ID
            start_date: Filter entries after ISO timestamp
            end_date: Filter entries before ISO timestamp
            
        Returns:
            dict with count, filters, and matching entries
        """
        from .tools.audit_log import get_audit_logger
        
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

