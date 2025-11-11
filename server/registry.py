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
    """Register MCP resources for policy configuration cards."""
    
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
    
    Tools are organized into categories:
    - Planning & Validation: render, validate, test, compare
    - Execution & Safety: apply, checkpoint, rollback
    - Discovery: 24+ network introspection tools
    - Direct Apply: sysctl, tc, nft, offloads, mtu
    """    
    @mcp.tool()
    def render_change_plan_tool(plan: dict) -> dict:
        """
        Render a ParameterPlan into concrete commands and scripts.
        
        Translates high-level optimization goals into executable system commands:
        - Sysctl: List of 'sysctl -w key=value' commands
        - TC: Bash script with traffic control commands
        - Nftables: Complete nftables ruleset script
        - Ethtool: NIC offload configuration commands
        - IP: MTU and interface configuration commands
        
        This tool has NO side effects - it only generates commands without executing them.
        Use apply_rendered_plan_tool() to actually apply the changes.
        
        Args:
            plan: ParameterPlan dictionary with iface, profile, changes, rationale
            
        Returns:
            RenderedPlan with sysctl_cmds, tc_script, nft_script, ethtool_cmds, ip_link_cmds
        """
        return render_change_plan(plan)
    
    @mcp.tool()
    def validate_change_plan_tool(parameter_plan: dict) -> dict:
        """
        Validate a ParameterPlan against schemas and policies.
        
        Performs multi-layer validation:
        1. Pydantic schema validation (types, required fields)
        2. Policy enforcement (limits from policy/limits.yaml)
        3. Interface validation (verify interface exists)
        4. Config card validation (parameters match specifications)
        
        Args:
            parameter_plan: ParameterPlan dictionary to validate
            
        Returns:
            ValidationResult with:
            - ok: bool (True if all validation passed)
            - issues: list of error messages (empty if ok=True)
            - normalized_plan: cleaned/normalized ParameterPlan
        """
        return validate_change_plan(parameter_plan)
    
    @mcp.tool()
    def apply_rendered_plan_tool(rendered_plan: dict, checkpoint_label: str = None) -> dict:
        """
        Apply a RenderedPlan atomically with automatic rollback on failure.
        
        Execution flow:
        1. Create checkpoint (snapshot current state)
        2. Execute sysctl commands sequentially
        3. Execute tc script (traffic control)
        4. Execute nftables script (firewall/QoS)
        5. Execute ethtool commands (NIC offloads)
        6. Execute ip link commands (MTU)
        7. On any error: automatic rollback to checkpoint
        
        Safety features:
        - Command allowlisting (only approved binaries)
        - No shell injection (commands as argv arrays)
        - Atomic operations (all-or-nothing)
        - Automatic rollback on failure
        - Detailed execution logging
        
        Args:
            rendered_plan: RenderedPlan from render_change_plan_tool()
            checkpoint_label: Optional label for the checkpoint
            
        Returns:
            ChangeReport with:
            - applied: bool (True if all commands succeeded)
            - errors: list of error messages
            - checkpoint_id: ID for manual rollback if needed
            - notes: execution log with ✓/✗ for each command
        """
        return apply_rendered_plan(rendered_plan, checkpoint_label)
    
    @mcp.tool()
    def snapshot_checkpoint_tool(label: str = None) -> dict:
        """
        Create a checkpoint of current network state for rollback.
        
        Snapshots include: sysctl parameters, tc qdisc config, nftables rules,
        NIC offloads, MTU settings. Used for manual checkpointing or testing.
        
        Args:
            label: Optional descriptive label for this checkpoint
            
        Returns:
            dict with checkpoint_id and creation timestamp
        """
        return snapshot_checkpoint(label)
    
    @mcp.tool()
    def rollback_to_checkpoint_tool(checkpoint_id: str) -> dict:
        """
        Restore network configuration from a checkpoint.
        
        Reverts all network settings to the state captured in the specified
        checkpoint. Use list_checkpoints_tool() to see available checkpoints.
        
        Args:
            checkpoint_id: The checkpoint ID to restore
            
        Returns:
            dict with ok status, restored settings, and notes
        """
        return rollback_to_checkpoint(checkpoint_id)
    
    @mcp.tool()
    def list_checkpoints_tool() -> dict:
        """List all available checkpoints with metadata (ID, label, timestamp)."""
        return list_checkpoints()
    
    @mcp.tool()
    def delete_checkpoint_tool(checkpoint_id: str) -> dict:
        """Delete a specific checkpoint to free up storage."""
        return delete_checkpoint(checkpoint_id)
    
    # ============================================================================
    # PERFORMANCE TESTING & VALIDATION
    # ============================================================================
    
    @mcp.tool()
    def test_network_performance_tool(profile: str = "gaming") -> dict:
        """
        Run comprehensive network performance benchmarks.
        
        Test suites by profile:
        - gaming: Focus on latency and jitter (20-30 pings, DNS timing, connection speed)
        - throughput: Bandwidth tests with iperf3 if available
        - balanced: Mixed tests with moderate samples
        - low-latency: Ultra-strict latency testing
        
        Use cases:
        - Establish baseline before making changes
        - Validate improvements after optimization
        - Troubleshoot network issues
        
        Returns:
            dict with latency, jitter, packet loss, DNS resolution, connection time,
            and optional throughput metrics
        """
        from .tools.validation_metrics import run_full_benchmark
        return run_full_benchmark(profile)
    
    @mcp.tool()
    def quick_latency_test_tool() -> dict:
        """
        Quick 10-ping latency test for rapid before/after comparisons.
        Useful during interactive optimization sessions.
        
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
        Compare before/after performance and decide: KEEP, ROLLBACK, or UNCERTAIN.
        
        Decision logic by profile:
        - gaming: Prioritizes latency (40%), jitter (30%), packet loss (20%), connection time (10%)
        - throughput: Prioritizes bandwidth (50%), stability (20%), retransmits (20%), connection (10%)
        - balanced: Equal weight to latency and throughput
        - low-latency: Ultra-strict on latency (any increase triggers ROLLBACK)
        
        Args:
            before_results: Output from test_network_performance_tool() BEFORE changes
            after_results: Output from test_network_performance_tool() AFTER changes
            profile: Validation profile (gaming, throughput, balanced, low-latency)
            
        Returns:
            dict with decision (KEEP/ROLLBACK/UNCERTAIN), score (0-100), summary,
            detailed reasons, and metrics comparison
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
        Validate changes and automatically rollback if performance degraded.
        
        Combines validate_configuration_changes_tool() + rollback_to_checkpoint_tool()
        for automated testing workflows.
        
        Args:
            checkpoint_id: Checkpoint to rollback to if validation fails
            before_results: Benchmark before changes
            after_results: Benchmark after changes
            profile: Validation profile
            auto_rollback: If True, automatically rollback on ROLLBACK decision
            
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
    
    # ============================================================================
    # DISCOVERY TOOLS
    # ============================================================================
    
    # Network Interface Discovery
    @mcp.tool()
    def ip_info() -> dict:
        """Network interfaces and IP addresses (ip addr show)"""
        return _disc.ip_info()
    
    @mcp.tool()
    def eth_info(iface: str = "eth0") -> dict:
        """Interface hardware capabilities and driver info (ethtool <iface>)"""
        return _disc.eth_info(iface)
    
    @mcp.tool()
    def hostname_ips() -> dict:
        """All IP addresses for local hostname (hostname -I)"""
        return _disc.hostname_ips()
    
    @mcp.tool()
    def hostnamectl() -> dict:
        """System hostname and OS metadata (hostnamectl status)"""
        return _disc.hostnamectl()
    
    # Network Manager & Wireless
    @mcp.tool()
    def nmcli_status() -> dict:
        """NetworkManager device connection status (nmcli device status)"""
        return _disc.nmcli_status()
    
    @mcp.tool()
    def iwconfig(iface: str = "wlan0") -> dict:
        """Wireless interface parameters (iwconfig <iface>)"""
        return _disc.iwconfig(iface)
    
    @mcp.tool()
    def iwlist_scan(iface: str = "wlan0", subcmd: str = "scan") -> dict:
        """Scan for available wireless networks (iwlist <iface> scan)"""
        return _disc.iwlist_scan(iface, subcmd)
    
    # ARP & Neighbor Discovery
    @mcp.tool()
    def arp_table() -> dict:
        """ARP table with IP-to-MAC mappings (arp -n)"""
        return _disc.arp_table()
    
    @mcp.tool()
    def ip_neigh() -> dict:
        """Neighbor cache for ARP and NDP (ip neigh show)"""
        return _disc.ip_neigh()
    
    @mcp.tool()
    def ip_route() -> dict:
        """Routing table (ip route show)"""
        return _disc.ip_route()
    
    # DNS Resolution
    @mcp.tool()
    def resolvectl_status() -> dict:
        """DNS resolver configuration (resolvectl status)"""
        return _disc.resolvectl_status()
    
    @mcp.tool()
    def cat_resolv_conf() -> dict:
        """/etc/resolv.conf contents (cat /etc/resolv.conf)"""
        return _disc.cat_resolv_conf()
    
    @mcp.tool()
    def dig(domain: str, dns: str | None = None) -> dict:
        """DNS query with dig (dig [@dns] <domain>)"""
        return _disc.dig(domain, dns)
    
    @mcp.tool()
    def host(domain: str) -> dict:
        """Simple DNS lookup (host <domain>)"""
        return _disc.host(domain)
    
    @mcp.tool()
    def nslookup(domain: str) -> dict:
        """Legacy DNS query (nslookup <domain>)"""
        return _disc.nslookup(domain)
    
    # Connectivity & Latency
    @mcp.tool()
    def ping_host(address: str, count: int = 3) -> dict:
        """ICMP reachability and latency test (ping -c <count> <address>)"""
        return _disc.ping_host(address, count)
    
    @mcp.tool()
    def traceroute(domain: str) -> dict:
        """Trace network path (traceroute <host>)"""
        return _disc.traceroute(domain)
    
    @mcp.tool()
    def tracepath(domain: str) -> dict:
        """Trace path without root (tracepath <host>)"""
        return _disc.tracepath(domain)
    
    # Sockets & Connections
    @mcp.tool()
    def ss_summary(options: str = "tulwn") -> dict:
        """Socket statistics and connections (ss -<options>)"""
        return _disc.ss_summary(options)
    
    # Traffic Control
    @mcp.tool()
    def tc_qdisc_show(iface: str) -> dict:
        """Traffic control qdisc config and stats (tc -s qdisc show dev <iface>)"""
        return _disc.tc_qdisc_show(iface)
    
    # Firewall & Filtering
    @mcp.tool()
    def nft_list_ruleset() -> dict:
        """Nftables firewall ruleset (nft list ruleset)"""
        return _disc.nft_list_ruleset()
    
    @mcp.tool()
    def iptables_list() -> dict:
        """Iptables firewall rules (iptables -L -v -n)"""
        return _disc.iptables_list()
    
    # ============================================================================
    # DIRECT APPLY TOOLS
    # ============================================================================
    
    @mcp.tool()
    def set_sysctl(kv: dict[str, str]) -> dict:
        """
        Apply sysctl kernel parameters directly.
        
        Executes 'sysctl -w key=value' for each parameter in sorted order.
        Stops on first error and returns partial results.
        
        Args:
            kv: Dictionary of sysctl parameter names to values
                Example: {"net.ipv4.tcp_congestion_control": "bbr", ...}
                
        Returns:
            dict with ok status, exit code, stdout, stderr
        """
        return _apply_sysctl.set_sysctl(kv)
    
    @mcp.tool()
    def apply_tc_script(lines: list[str]) -> dict:
        """
        Execute traffic control (tc) commands from a script.
        
        Runs each tc command line sequentially. Use for qdisc, class, and filter
        configuration. Commands should not include shebang or comments.
        
        Args:
            lines: List of tc command strings (e.g., ["tc qdisc add dev eth0 root fq", ...])
            
        Returns:
            dict with ok status, exit code, stdout, stderr
        """
        return _apply_tc.apply_tc_script(lines)
    
    @mcp.tool()
    def apply_nft_ruleset(ruleset: str) -> dict:
        """
        Apply a complete nftables ruleset via 'nft -f'.
        
        The ruleset should be a complete nftables configuration with tables,
        chains, and rules. Use flush rules to clear existing state if needed.
        
        Args:
            ruleset: Complete nftables configuration as string
            
        Returns:
            dict with ok status, exit code, stdout, stderr
        """
        return _apply_nft.apply_nft_ruleset(ruleset)
    
    # ============================================================================
    # AUDIT LOG TOOLS
    # ============================================================================
    
    @mcp.tool()
    def get_audit_log_tool(limit: int = 50) -> dict:
        """
        Get recent audit log entries showing all system changes.
        
        Returns a history of all configuration changes, commands executed,
        validations performed, and rollback operations with timestamps and context.
        
        Args:
            limit: Maximum number of recent entries to return (default: 50)
            
        Returns:
            dict with entries list containing audit log records
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
        
        Filter audit log by action type, checkpoint ID, or date range.
        All filters are optional and can be combined.
        
        Args:
            action: Filter by action type (e.g., 'apply_plan', 'validate_plan', 
                   'create_checkpoint', 'rollback', 'execute_command', 'validation_test')
            checkpoint_id: Filter by specific checkpoint ID
            start_date: Filter entries after this ISO timestamp
            end_date: Filter entries before this ISO timestamp
            
        Returns:
            dict with matching entries list
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
    
