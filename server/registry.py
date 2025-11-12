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
from .tools.audit_log import get_audit_logger
import tempfile
from .tools.validation_metrics import run_full_benchmark
from .tools.validation_engine import ValidationEngine


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

#  Checkpointing Part

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
    
    # Benchmarking and Testing Tools

    @mcp.tool()
    def test_network_performance_tool(profile: str = "gaming") -> dict:
        """
        Run comprehensive network performance benchmarks.
        
        Executes profile-specific tests to measure latency, jitter, packet loss,
        DNS resolution, and connection speeds. Use before and after configuration
        changes to measure impact.
        
        Profiles (from profiles.yaml):
        - gaming: Latency and jitter focused (30 pings, multi-host tests)
        - streaming: Bandwidth tests with iperf3 (10-second tests)
        - video_calls: Balanced tests for video conferencing
        - bulk_transfer: Maximum throughput testing (60-second iperf3)
        - server: Server workload testing with concurrency focus
        - balanced: Mixed tests with moderate samples
        
        Args:
            profile: Test profile to use
            
        Returns:
            dict with latency, jitter, packet_loss, dns_resolution,
            connection_time, and optional throughput metrics
        """
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
        - streaming: Bandwidth 50%, latency stability 20%, retransmits 20%, connection 10%
        - video_calls: Latency 35%, jitter 35%, packet loss 20%, connection 10%
        - bulk_transfer: Throughput 70%, stability 15%, retransmits 15%
        - server: Latency stability 30%, connection reliability 30%, throughput 20%, DNS 20%
        - balanced: Equal weight to gaming and streaming criteria
        - low-latency: Ultra-strict on latency (any increase triggers ROLLBACK)
        
        Supported profiles: gaming, streaming, video_calls, bulk_transfer, server, balanced, low-latency
        Legacy alias: throughput → streaming
        
        Args:
            before_results: Benchmark before changes
            after_results: Benchmark after changes
            profile: Validation profile
            
        Returns:
            dict with decision, score (0-100), summary, reasons, and
            detailed metrics comparison
        """
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
    
        
# Discovery Tools
    
    @mcp.tool()
    def ip_info() -> dict:
                """
                Discover network interfaces and their addressing information.

                Returns:
                        dict: A structured result describing local network interfaces. Typical
                        keys include:
                            - ok (bool): True if the discovery completed without fatal errors.
                            - interfaces (dict): Mapping of interface name -> metadata where
                                metadata commonly contains addresses, MAC, state, mtu, and flags.
                            - errors (list): List of non-fatal warnings or error messages.

                Notes:
                        - This is a read-only discovery operation. It should not modify
                            system state.
                        - May require elevated privileges for certain low-level details,
                            but will return best-effort information for unprivileged users.
                """
                return _disc.ip_info()
    
    @mcp.tool()
    def eth_info(iface: str = "eth0") -> dict:
        """
        Retrieve detailed hardware and driver information for a network interface.

        Args:
            iface (str): Name of the network interface to inspect (e.g. "eth0").

        Returns:
            dict: Structured metadata including fields such as:
              - ok (bool): True when the query succeeds
              - name (str): Interface name
              - driver (str|None): Kernel driver in use if available
              - firmware (str|None): Firmware version when available
              - speed (int|None): Reported link speed in Mbps
              - duplex (str|None): duplex mode (full/half)
              - features (list): offload/caps supported by the NIC
              - errors (list): Any warnings or errors encountered

        Error modes:
            - If the interface does not exist, ok will be False and an error
              message will be present in errors.

        Notes:
            - Implementation may call ethtool or read sysfs. Availability of
              fields depends on the host and permissions.
        """
        return _disc.eth_info(iface)
    
    @mcp.tool()
    def hostname_ips() -> dict:
        """
        Resolve the local hostname to all configured IP addresses.

        Returns:
            dict: {
              "ok": bool,
              "hostname": str,
              "addresses": list of {"family": "ipv4"|"ipv6", "address": str},
              "errors": list
            }

        Notes:
            - This performs a local name resolution (gethostname + DNS/hosts
              lookup) and enumerates addresses configured for that name.
            - Useful for discovering which addresses the system will advertise.
        """
        return _disc.hostname_ips()
    
    @mcp.tool()
    def hostnamectl() -> dict:
        """
        Collect system identity and operating system metadata.

        Returns:
            dict: Typical keys:
              - ok (bool)
              - static_hostname (str|None)
              - transient_hostname (str|None)
              - pretty_hostname (str|None)
              - chassis, deployment, icon_name (optional strings)
              - os (str), kernel (str), architecture (str)
              - errors (list)

        Notes:
            - This is analogous to the output of `hostnamectl` on systemd
              systems but should degrade gracefully on other systems.
        """
        return _disc.hostnamectl()
    
    @mcp.tool()
    def nmcli_status() -> dict:
        """
        Query NetworkManager for device and connection status.

        Returns:
            dict: {
              "ok": bool,
              "devices": list of device-status entries,
              "connections": list of known connections,
              "errors": list
            }

        Args:
            - This call typically shells out to `nmcli` and parses its output.

        Error modes:
            - If NetworkManager is not present, ok will be False and an
              explanatory error will be returned.
        """
        return _disc.nmcli_status()
    
    @mcp.tool()
    def iwconfig(iface: str = "wlan0") -> dict:
        """
        Get wireless interface parameters (link quality, ESSID, mode, freq).

        Args:
            iface (str): Wireless interface name (default: "wlan0").

        Returns:
            dict: {
              "ok": bool,
              "interface": str,
              "essid": str|None,
              "mode": str|None,
              "frequency": str|None,
              "link_quality": str|None,
              "bit_rate": str|None,
              "errors": list
            }

        Notes:
            - May rely on legacy `iwconfig` output; on modern systems `iw` may
              provide more detailed information. Availability depends on
              wireless drivers and permissions.
        """
        return _disc.iwconfig(iface)
    
    @mcp.tool()
    def iwlist_scan(iface: str = "wlan0", subcmd: str = "scan") -> dict:
        """
        Perform a wireless scan on the given interface and return available
        networks.

        Args:
            iface (str): Wireless interface to scan (default: "wlan0").
            subcmd (str): iwlist subcommand to run (commonly "scan").

        Returns:
            dict: {
              "ok": bool,
              "networks": list of {ssid, bssid, channel, freq, signal, security},
              "errors": list
            }

        Notes:
            - Scanning may require elevated privileges and may briefly
              interrupt the wireless connection.
        """
        return _disc.iwlist_scan(iface, subcmd)
    
    @mcp.tool()
    def arp_table() -> dict:
        """
        Retrieve the system ARP table (IPv4) and neighbor table (NDP for IPv6).

        Returns:
            dict: {
              "ok": bool,
              "entries": list of {ip, mac, iface, state},
              "errors": list
            }

        Notes:
            - The function returns both ARP and neighbor cache entries when
              available for convenience.
        """
        return _disc.arp_table()
    
    @mcp.tool()
    def ip_neigh() -> dict:
        """
        Return the kernel neighbor cache for ARP (IPv4) and NDP (IPv6).

        Returns:
            dict: {
              "ok": bool,
              "neighbors": list of {ip, lladdr, dev, state, used},
              "errors": list
            }

        Notes:
            - Useful for diagnosing neighbor resolution issues and stale
              entries on multi-homed systems.
        """
        return _disc.ip_neigh()
    
    @mcp.tool()
    def ip_route() -> dict:
        """
        Return the system routing table information.

        Returns:
            dict: {
              "ok": bool,
              "routes": list of route entries (dst, via, dev, proto, scope, metric),
              "errors": list
            }

        Notes:
            - The output is analogous to `ip route show` and may include
              multiple routing tables and multipath routes.
        """
        return _disc.ip_route()
    
    @mcp.tool()
    def resolvectl_status() -> dict:
        """
        Query systemd-resolved (if present) for resolver status and links.

        Returns:
            dict: {
              "ok": bool,
              "servers": list,
              "links": list,
              "cache": dict|None,
              "errors": list
            }

        Notes:
            - If systemd-resolved is not available this will return an
              informative error and the caller should fall back to other
              resolver data (e.g. /etc/resolv.conf).
        """
        return _disc.resolvectl_status()
    
    @mcp.tool()
    def cat_resolv_conf() -> dict:
        """
        Read and return the contents of /etc/resolv.conf.

        Returns:
            dict: {
              "ok": bool,
              "path": "/etc/resolv.conf",
              "content": str,
              "parsed": list of {type: 'nameserver'|'search'|'options', value},
              "errors": list
            }

        Notes:
            - The file may be a symlink managed by systemd-resolved or NetworkManager.
            - This is a best-effort, read-only operation and will not modify
              system configuration.
        """
        return _disc.cat_resolv_conf()
    
    @mcp.tool()
    def dig(domain: str, dns: str | None = None) -> dict:
        """
        Perform a DNS lookup using `dig`-style semantics.

        Args:
            domain (str): Domain name to query.
            dns (str|None): Optional specific DNS server to query (IP or host).

        Returns:
            dict: {
              "ok": bool,
              "question": {"name": domain, "server": dns or system default},
              "answers": list of resource records,
              "raw": str (raw dig output),
              "errors": list
            }

        Notes:
            - This is intended for diagnostic lookups (A, AAAA, CNAME, TXT, etc.).
            - If `dig` is not available the implementation should fall back to
              a python resolver and still provide structured results.
        """
        return _disc.dig(domain, dns)
    
    @mcp.tool()
    def host(domain: str) -> dict:
        """
        Perform a simple DNS lookup similar to the `host` utility.

        Args:
            domain (str): Domain or hostname to resolve.

        Returns:
            dict: {"ok": bool, "name": domain, "addresses": [str], "errors": []}

        Notes:
            - Prefer this for quick forward lookups; use `dig` for richer
              DNS query control.
        """
        return _disc.host(domain)
    
    @mcp.tool()
    def nslookup(domain: str) -> dict:
        """
        Run a legacy DNS query similar to `nslookup` to retrieve name->IP
        mappings and authoritative server info.

        Args:
            domain (str): Domain to query.

        Returns:
            dict: {
              "ok": bool,
              "server": resolver used,
              "answers": list,
              "authority": list,
              "raw": str,
              "errors": list
            }

        Notes:
            - `nslookup` historically behaved differently from `dig`; maintain
              compatibility for users who rely on its output format.
        """
        return _disc.nslookup(domain)
    
    @mcp.tool()
    def ping_host(address: str, count: int = 3) -> dict:
        """
        Send ICMP echo requests to measure reachability and latency.

        Args:
            address (str): Hostname or IP address to ping.
            count (int): Number of ICMP echo requests to send (default: 3).

        Returns:
            dict: {
              "ok": bool,
              "transmitted": int,
              "received": int,
              "packet_loss_pct": float,
              "rtt": {"min": float, "avg": float, "max": float, "mdev": float},
              "raw": str,
              "errors": list
            }

        Error modes:
            - If ICMP is blocked or the command lacks privileges, ok will be
              False and an explanatory error will be included.
        """
        return _disc.ping_host(address, count)
    
    @mcp.tool()
    def traceroute(domain: str) -> dict:
        """
        Perform a traceroute to a destination showing hop-by-hop path and
        round-trip times.

        Args:
            domain (str): Target hostname or IP for traceroute.

        Returns:
            dict: {
              "ok": bool,
              "hops": list of {ttl, addr, rtts: [float], hostnames: [str]},
              "raw": str,
              "errors": list
            }

        Notes:
            - May require elevated privileges to use certain probe types; will
              fall back to UDP/TCP probes when possible.
        """
        return _disc.traceroute(domain)
    
    @mcp.tool()
    def tracepath(domain: str) -> dict:
        """
        Perform a path trace similar to `tracepath` which does not require
        root privileges. Provides hop counts and MTU discovery information.

        Args:
            domain (str): Target hostname or IP.

        Returns:
            dict: {"ok": bool, "hops": list, "mtu": int|None, "raw": str, "errors": []}

        Notes:
            - Less precise than `traceroute` but safer for non-privileged use.
        """
        return _disc.tracepath(domain)
    
    @mcp.tool()
    def ss_summary(options: str = "tulwn") -> dict:
        """
        Retrieve socket statistics and active connections using `ss` semantics.

        Args:
            options (str): Options string passed to `ss` (default "tulwn").

        Returns:
            dict: {
              "ok": bool,
              "summary": dict with counts by state/protocol,
              "connections": list of connection entries,
              "raw": str,
              "errors": list
            }

        Notes:
            - This is useful for debugging listening sockets, established
              connections, and port usage on the host.
        """
        return _disc.ss_summary(options)
    
    @mcp.tool()
    def tc_qdisc_show(iface: str) -> dict:
        """
        Show traffic control qdisc configuration and statistics for an
        interface.

        Args:
            iface (str): Network interface to query.

        Returns:
            dict: {
              "ok": bool,
              "interface": str,
              "qdiscs": list of qdisc entries (type, parent, handle, params),
              "classes": list,
              "filters": list,
              "errors": list
            }

        Notes:
            - Implementation may call `tc qdisc show dev <iface>` and related
              commands. Requires appropriate privileges to read some counters.
        """
        return _disc.tc_qdisc_show(iface)
    
    @mcp.tool()
    def nft_list_ruleset() -> dict:
        """
        Retrieve the active nftables ruleset from the system.

        Returns:
            dict: {"ok": bool, "ruleset": str, "parsed": dict|None, "errors": []}

        Notes:
            - This typically shells out to `nft list ruleset` and returns the
              raw ruleset. If parsing is implemented, a structured representation
              will be included in `parsed`.
        """
        return _disc.nft_list_ruleset()
    
    @mcp.tool()
    def iptables_list() -> dict:
        """
        Return the current iptables rules (legacy IPv4/IPv6 tables).

        Returns:
            dict: {"ok": bool, "tables": dict, "raw": str, "errors": list}

        Notes:
            - On systems using nftables as the backend, iptables output may be
              emulated. This function returns the best-effort representation of
              configured firewall rules.
        """
        return _disc.iptables_list()
    
# Applying Tools
    
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
    
# AUDIT LOGGING
    
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

