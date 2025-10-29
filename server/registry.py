def register_resources(mcp, policy_registry):
    """
    Register policy configuration cards as MCP resources.
    The LLM can read these resources to understand available network optimization options.
    """
    import json
    
    @mcp.resource("policy://config_cards/list")
    def get_policy_card_list() -> str:
        """
        Get a list of all available network optimization configuration cards.
        Each card represents a specific network parameter that can be configured.
        """
        cards = policy_registry.list()
        return json.dumps({
            "description": "Available network optimization configuration cards",
            "count": len(cards),
            "cards": cards
        }, indent=2)
    
    @mcp.resource("policy://config_cards/{card_id}")
    def get_policy_card(card_id: str) -> str:
        """
        Get detailed information about a specific configuration card.
        Includes description, use cases, parameters, impacts, and examples.
        """
        card = policy_registry.get(card_id)
        if not card:
            return json.dumps({"error": f"Configuration card '{card_id}' not found"})
        return json.dumps(card, indent=2)


def register_tools(mcp):
    """
    Register all tools with the FastMCP server using decorators.
    These tools allow the LLM to plan, validate, and apply network optimizations.
    """
    from .tools.planner import render_change_plan
    from .tools.validator import validate_change_plan
    from .tools.apply.apply import apply_rendered_plan
    from .tools.apply.checkpoints import snapshot_checkpoint, rollback_to_checkpoint
    # MCP Tools implementation exposure
    from .tools import discovery as _disc
    from .tools.apply import sysctl as _apply_sysctl, tc as _apply_tc, nft as _apply_nft, offloads as _apply_off, mtu as _apply_mtu
    
    @mcp.tool()
    def render_change_plan_tool(plan: dict) -> dict:
        """
        Render a ParameterPlan into concrete command lists/scripts. No side effects.
        
        Args:
            plan: A ParameterPlan dictionary containing the network changes to render
            
        Returns:
            A RenderedPlan dictionary with executable commands and scripts
        """
        return render_change_plan(plan)
    
    @mcp.tool()
    def validate_change_plan_tool(parameter_plan: dict) -> dict:
        """
        Schema + policy validation for a ParameterPlan.
        
        Args:
            parameter_plan: A ParameterPlan dictionary to validate
            
        Returns:
            A ValidationResult with ok status and any issues found
        """
        return validate_change_plan(parameter_plan)
    
    @mcp.tool()
    def apply_rendered_plan_tool(rendered_plan: dict, checkpoint_label: str = None) -> dict:
        """
        Apply a previously rendered plan atomically, with rollback on failure.
        
        Args:
            rendered_plan: A RenderedPlan dictionary with commands to execute
            checkpoint_label: Optional label for the checkpoint created before applying changes
            
        Returns:
            A ChangeReport with status, errors, and checkpoint information
        """
        return apply_rendered_plan(rendered_plan, checkpoint_label)
    
    @mcp.tool()
    def snapshot_checkpoint_tool(label: str = None) -> dict:
        """
        Save the current network state for rollback.
        
        Args:
            label: Optional label to identify this checkpoint
            
        Returns:
            Dictionary with checkpoint_id and notes
        """
        return snapshot_checkpoint(label)
    
    @mcp.tool()
    def rollback_to_checkpoint_tool(checkpoint_id: str) -> dict:
        """
        Restore a previously saved network state.
        
        Args:
            checkpoint_id: The ID of the checkpoint to restore
            
        Returns:
            Dictionary with ok status and restoration notes
        """
        return rollback_to_checkpoint(checkpoint_id)

    # --- Discovery tools ---
    
    # Network Interface Discovery
    
    @mcp.tool()
    def ip_info() -> dict:
        """
        Retrieve all network interfaces and their IP addresses.
        
        Executes: ip addr show
        
        Returns:
            dict: Network interface information including:
                - ok: bool - Success status
                - code: int - Command exit code
                - stdout: str - Interface names, MAC addresses, and IP addresses (IPv4/IPv6)
                - stderr: str - Error message if command failed
        
        Use cases:
            - Identify all available network interfaces on the system
            - Check assigned IP addresses (both IPv4 and IPv6)
            - Verify interface naming conventions (eth0, wlan0, etc.)
            - Baseline discovery for network optimization
        
        Prerequisites: No additional tools required (ip command is standard)
        """
        return _disc.ip_info()

    @mcp.tool()
    def eth_info(iface: str = "eth0") -> dict:
        """
        Query interface hardware capabilities and driver information.
        
        Executes: ethtool <iface>
        
        Args:
            iface: str - Network interface name (default: "eth0")
        
        Returns:
            dict: Hardware and driver details including:
                - ok: bool - Success status
                - code: int - Command exit code
                - stdout: str - Link speed, duplex mode, driver name, and capabilities
                - stderr: str - Error message if command failed
        
        Use cases:
            - Check interface speed and duplex settings (1Gbps, 10Gbps, full/half duplex)
            - Identify driver version and firmware information
            - Verify supported offload capabilities (TSO, GSO, LRO, GRO, RXCSUM, TXCSUM)
            - Diagnose hardware incompatibilities before optimization
        
        Prerequisites: ethtool utility (usually in /usr/sbin; may need to be added to PATH)
        """
        return _disc.eth_info(iface)

    @mcp.tool()
    def hostname_ips() -> dict:
        """
        Get all IP addresses associated with the local hostname.
        
        Executes: hostname -I
        
        Returns:
            dict: Host IP addresses including:
                - ok: bool - Success status
                - code: int - Command exit code
                - stdout: str - Space-separated list of IP addresses
                - stderr: str - Error message if command failed
        
        Use cases:
            - Quick check of assigned IPs without parsing full interface details
            - Verify hostname resolution
            - List all active IPs for connectivity validation
        
        Prerequisites: No additional tools required
        """
        return _disc.hostname_ips()

    @mcp.tool()
    def hostnamectl() -> dict:
        """
        Retrieve system hostname and OS metadata.
        
        Executes: hostnamectl status
        
        Returns:
            dict: System identification including:
                - ok: bool - Success status
                - code: int - Command exit code
                - stdout: str - Hostname(s), operating system, kernel version, architecture
                - stderr: str - Error message if command failed
        
        Use cases:
            - Identify system for network policy application
            - Verify OS compatibility with optimization techniques
            - Collect baseline hardware architecture information
        
        Prerequisites: No additional tools required (systemd standard)
        """
        return _disc.hostnamectl()

    # Network Manager & Wireless Discovery
    
    @mcp.tool()
    def nmcli_status() -> dict:
        """
        Query NetworkManager device connection status.
        
        Executes: nmcli device status
        
        Returns:
            dict: Device and connection information including:
                - ok: bool - Success status
                - code: int - Command exit code
                - stdout: str - Device names, connection types, and status
                - stderr: str - Error message if command failed
        
        Use cases:
            - Check which interfaces are managed by NetworkManager
            - Verify active connections and their types (ethernet, wifi, vpn)
            - Troubleshoot connectivity issues
        
        Prerequisites: NetworkManager and nmcli utility must be installed
        Note: Fails gracefully if NetworkManager is not running
        """
        return _disc.nmcli_status()

    @mcp.tool()
    def iwconfig(iface: str = "wlan0") -> dict:
        """
        Retrieve wireless interface parameters and configuration.
        
        Executes: iwconfig <iface>
        
        Args:
            iface: str - Wireless interface name (default: "wlan0")
        
        Returns:
            dict: Wireless configuration including:
                - ok: bool - Success status
                - code: int - Command exit code
                - stdout: str - ESSID, frequency, signal strength, transmission power, encryption
                - stderr: str - Error message if command failed
        
        Use cases:
            - Check wireless signal strength and quality
            - Verify Wi-Fi frequency band (2.4 GHz vs 5 GHz)
            - Identify encryption method (WEP, WPA, WPA2, WPA3)
            - Diagnose Wi-Fi connectivity issues
        
        Prerequisites: wireless-tools package must be installed
        """
        return _disc.iwconfig(iface)

    @mcp.tool()
    def iwlist_scan(iface: str = "wlan0", subcmd: str = "scan") -> dict:
        """
        Scan for available wireless networks or retrieve detailed Wi-Fi information.
        
        Executes: iwlist <iface> <subcmd>
        
        Args:
            iface: str - Wireless interface name (default: "wlan0")
            subcmd: str - Subcommand to execute (default: "scan"; others: "freq", "keys", etc.)
        
        Returns:
            dict: Wireless network information including:
                - ok: bool - Success status
                - code: int - Command exit code
                - stdout: str - List of available networks with SSID, frequency, signal level, security
                - stderr: str - Error message if command failed
        
        Use cases:
            - List available wireless networks in range
            - Discover channel congestion and interference
            - Check available security standards (WEP, WPA2, WPA3)
            - Plan Wi-Fi channel optimization
        
        Prerequisites: wireless-tools package must be installed
        Note: May require elevated privileges (root) to scan
        Note: Timeout set to 10s as scanning can take longer than typical commands
        """
        return _disc.iwlist_scan(iface, subcmd)

    # ARP & Neighbor Discovery
    
    @mcp.tool()
    def arp_table() -> dict:
        """
        Display the system ARP (Address Resolution Protocol) table.
        
        Executes: arp -n
        
        Returns:
            dict: ARP entries including:
                - ok: bool - Success status
                - code: int - Command exit code
                - stdout: str - IP-to-MAC address mappings, interface names, types
                - stderr: str - Error message if command failed
        
        Use cases:
            - Verify neighboring hosts and their MAC addresses
            - Detect ARP spoofing or suspicious MAC addresses
            - Understand local network topology
            - Troubleshoot Layer 2 connectivity issues
        
        Prerequisites: net-tools package may need to be installed
        Note: This tool shows cached entries; does not create new ARP requests
        """
        return _disc.arp_table()

    @mcp.tool()
    def ip_neigh() -> dict:
        """
        Display the neighbor cache including ARP (IPv4) and NDP (IPv6) entries.
        
        Executes: ip neigh show
        
        Returns:
            dict: Neighbor cache information including:
                - ok: bool - Success status
                - code: int - Command exit code
                - stdout: str - IP addresses, MAC addresses, states (REACHABLE, STALE, FAILED), interfaces
                - stderr: str - Error message if command failed
        
        Use cases:
            - Check neighbor states for IPv4 and IPv6
            - Identify unreachable neighbors
            - Monitor neighbor state transitions
            - Troubleshoot IPv6 connectivity
        
        Prerequisites: No additional tools required (iproute2 standard)
        Advantage over arp_table: Supports both IPv4 and IPv6; shows neighbor states
        """
        return _disc.ip_neigh()

    # Routing Discovery
    
    @mcp.tool()
    def ip_route() -> dict:
        """
        Display the system routing table.
        
        Executes: ip route show
        
        Returns:
            dict: Routing information including:
                - ok: bool - Success status
                - code: int - Command exit code
                - stdout: str - Destination networks, gateways, metrics, interfaces, protocols
                - stderr: str - Error message if command failed
        
        Use cases:
            - Verify default gateway and routing paths
            - Check policy-based routing rules
            - Identify asymmetric routing issues
            - Plan network optimization based on routing topology
        
        Prerequisites: No additional tools required (iproute2 standard)
        """
        return _disc.ip_route()

    # DNS Discovery
    
    @mcp.tool()
    def resolvectl_status() -> dict:
        """
        Query systemd-resolved DNS resolver status and configuration.
        
        Executes: resolvectl status
        
        Returns:
            dict: DNS resolver information including:
                - ok: bool - Success status
                - code: int - Command exit code
                - stdout: str - Configured DNS servers, search domains, DNSSEC settings, cache statistics
                - stderr: str - Error message if command failed
        
        Use cases:
            - Check DNS servers in use (system-wide and per-interface)
            - Verify DNSSEC validation status
            - Monitor DNS cache performance
            - Troubleshoot DNS resolution issues
        
        Prerequisites: systemd-resolved must be running
        Note: Provides more detailed information than /etc/resolv.conf on systemd systems
        """
        return _disc.resolvectl_status()

    @mcp.tool()
    def cat_resolv_conf() -> dict:
        """
        Display the static DNS resolver configuration file.
        
        Executes: cat /etc/resolv.conf
        
        Returns:
            dict: Resolver configuration including:
                - ok: bool - Success status
                - code: int - Command exit code
                - stdout: str - nameserver entries, options, search domains
                - stderr: str - Error message if command failed
        
        Use cases:
            - Check configured DNS servers on traditional systems
            - Verify resolver configuration for troubleshooting
            - Identify custom DNS settings
        
        Prerequisites: No additional tools required
        Note: On systemd systems, this file may be a symlink to systemd-resolved config
        """
        return _disc.cat_resolv_conf()

    @mcp.tool()
    def dig(domain: str, dns: str | None = None) -> dict:
        """
        Perform a DNS query using the dig (Domain Information Groper) tool.
        
        Executes: dig [@dns] <domain>
        
        Args:
            domain: str - Domain name to query (e.g., "example.com")
            dns: str | None - Optional specific DNS server to query (e.g., "8.8.8.8")
        
        Returns:
            dict: DNS query results including:
                - ok: bool - Success status
                - code: int - Command exit code
                - stdout: str - Query response with section headers (QUESTION, ANSWER, AUTHORITY, ADDITIONAL)
                - stderr: str - Error message if command failed
        
        Use cases:
            - Verify DNS resolution works correctly
            - Test specific DNS servers
            - Debug DNS propagation issues
            - Check DNS record types (A, AAAA, MX, CNAME, TXT, NS, etc.)
            - Diagnose DNS performance problems
        
        Prerequisites: dnsutils or bind9-host package must be installed
        """
        return _disc.dig(domain, dns)

    @mcp.tool()
    def host(domain: str) -> dict:
        """
        Perform a simple DNS lookup using the host utility.
        
        Executes: host <domain>
        
        Args:
            domain: str - Domain name to look up (e.g., "example.com")
        
        Returns:
            dict: DNS lookup results including:
                - ok: bool - Success status
                - code: int - Command exit code
                - stdout: str - Resolved IP address(es) and any additional records
                - stderr: str - Error message if command failed
        
        Use cases:
            - Quick DNS resolution check
            - Verify A and AAAA records
            - Simple domain-to-IP translation
            - Lightweight alternative to dig for basic queries
        
        Prerequisites: bind9-host package must be installed
        """
        return _disc.host(domain)

    @mcp.tool()
    def nslookup(domain: str) -> dict:
        """
        Perform a DNS query using the legacy nslookup utility.
        
        Executes: nslookup <domain>
        
        Args:
            domain: str - Domain name to query (e.g., "example.com")
        
        Returns:
            dict: DNS query results including:
                - ok: bool - Success status
                - code: int - Command exit code
                - stdout: str - Query response in nslookup format (server info, addresses)
                - stderr: str - Error message if command failed
        
        Use cases:
            - Legacy DNS queries for compatibility
            - Interactive-like DNS lookups
            - Cross-platform DNS verification
        
        Prerequisites: dnsutils package must be installed
        Note: Considered legacy; dig and host are generally preferred for scripting
        """
        return _disc.nslookup(domain)

    # Connectivity & Latency Discovery
    
    @mcp.tool()
    def ping_host(address: str, count: int = 3) -> dict:
        """
        Test ICMP reachability and measure latency to a host.
        
        Executes: ping -c <count> <addr>
        
        Args:
            address: str - Target IP address or hostname (e.g., "8.8.8.8", "example.com")
            count: int - Number of ICMP echo requests to send (default: 3)
        
        Returns:
            dict: ICMP ping results including:
                - ok: bool - Success status
                - code: int - Command exit code (0 = all packets received, 1 = some lost)
                - stdout: str - Packet statistics, min/avg/max/stddev latency
                - stderr: str - Error message if command failed
        
        Use cases:
            - Verify host reachability
            - Measure round-trip latency and jitter
            - Detect packet loss
            - Test network connectivity before optimization
        
        Prerequisites: No additional tools required (ping is standard)
        Note: Timeout is automatically adjusted based on count (5s + count seconds)
        """
        return _disc.ping_host(address, count)

    @mcp.tool()
    def traceroute(host: str) -> dict:
        """
        Trace the network path to a destination host using UDP packets.
        
        Executes: traceroute <host>
        
        Args:
            host: str - Target hostname or IP address
        
        Returns:
            dict: Traceroute results including:
                - ok: bool - Success status
                - code: int - Command exit code
                - stdout: str - Sequence of hops with hostnames, IP addresses, and latencies
                - stderr: str - Error message if command failed
        
        Use cases:
            - Identify network hops and routing path to destination
            - Diagnose routing issues or asymmetric paths
            - Locate latency bottlenecks in network path
            - Detect MTU/fragmentation issues
        
        Prerequisites: traceroute package must be installed
        Note: May require elevated privileges (root) or special permissions
        Note: Timeout set to 20s as traceroute can be slow
        Note: Uses UDP probes by default (may be blocked by some firewalls)
        """
        return _disc.traceroute(host)

    @mcp.tool()
    def tracepath(host: str) -> dict:
        """
        Trace network path to a destination without requiring elevated privileges.
        
        Executes: tracepath <host>
        
        Args:
            host: str - Target hostname or IP address
        
        Returns:
            dict: Tracepath results including:
                - ok: bool - Success status
                - code: int - Command exit code
                - stdout: str - Sequence of hops with latencies and path information
                - stderr: str - Error message if command failed
        
        Use cases:
            - Trace path to destination (non-root alternative to traceroute)
            - Diagnose routing and MTU issues
            - Identify latency-contributing hops
            - Works in unprivileged containers and sandboxes
        
        Prerequisites: iputils-tracepath package must be installed
        Advantage over traceroute: Does not require root privileges
        Note: Timeout set to 20s as tracepath can be slow
        """
        return _disc.tracepath(host)

    # Socket & Connection Discovery
    
    @mcp.tool()
    def ss_summary(options: str = "tulwn") -> dict:
        """
        Display active sockets and connections using the ss utility.
        
        Executes: ss -<options>
        
        Args:
            options: str - ss command flags (default: "tulwn")
                - t: TCP sockets
                - u: UDP sockets
                - l: Listening sockets
                - w: Raw sockets
                - n: Numeric addresses/ports
                - Additional options: a (all), p (processes), s (statistics), etc.
        
        Returns:
            dict: Socket and connection information including:
                - ok: bool - Success status
                - code: int - Command exit code
                - stdout: str - Socket state, source/dest IP:port, associated processes
                - stderr: str - Error message if command failed
        
        Use cases:
            - List active TCP/UDP connections
            - Check listening ports and services
            - Monitor socket states (ESTABLISHED, TIME_WAIT, etc.)
            - Troubleshoot connection issues
            - Verify firewall/NAT configuration effects
        
        Prerequisites: No additional tools required (iproute2 standard)
        Note: Default options (tulwn) show TCP, UDP, listening, raw, and numeric output
        """
        return _disc.ss_summary(options)

    # Traffic Control Discovery
    
    @mcp.tool()
    def tc_qdisc_show(iface: str) -> dict:
        """
        Display Traffic Control (tc) queue discipline (qdisc) configuration and statistics.
        
        Executes: tc -s qdisc show dev <iface>
        
        Args:
            iface: str - Network interface name (e.g., "eth0", "wlan0")
        
        Returns:
            dict: Qdisc configuration and statistics including:
                - ok: bool - Success status
                - code: int - Command exit code
                - stdout: str - Qdisc type, parameters, backlog, drops, overlimits
                - stderr: str - Error message if command failed
        
        Use cases:
            - Verify current qdisc (pfifo_fast, HTB, fq, cake, etc.)
            - Check queue statistics (packets dropped, backlog size)
            - Monitor QoS performance
            - Diagnose buffering issues
        
        Prerequisites: iproute2 with tc support (standard)
        """
        return _disc.tc_qdisc_show(iface)

    # Firewall & Filtering Discovery
    
    @mcp.tool()
    def nft_list_ruleset() -> dict:
        """
        Display the complete nftables firewall ruleset.
        
        Executes: nft list ruleset
        
        Returns:
            dict: Nftables ruleset including:
                - ok: bool - Success status
                - code: int - Command exit code
                - stdout: str - Tables, chains, rules with match conditions and actions
                - stderr: str - Error message if command failed
        
        Use cases:
            - Inspect nftables firewall rules
            - Verify rule application before optimization
            - Diagnose packet filtering issues
            - Baseline firewall configuration
        
        Prerequisites: nftables package must be installed
        Note: Requires root/elevated privileges to execute
        """
        return _disc.nft_list_ruleset()

    @mcp.tool()
    def iptables_list() -> dict:
        """
        Display the iptables firewall rules and packet statistics.
        
        Executes: iptables -L -v -n
        
        Returns:
            dict: Iptables rules including:
                - ok: bool - Success status
                - code: int - Command exit code
                - stdout: str - Chain names, rules with targets, packet/byte counters
                - stderr: str - Error message if command failed
        
        Use cases:
            - Inspect legacy iptables firewall configuration
            - Verify packet filtering and NAT rules
            - Monitor packet/byte counters
            - Troubleshoot firewall-related performance issues
        
        Prerequisites: iptables package must be installed
        Note: Requires root/elevated privileges to execute
        Note: Use nft_list_ruleset for modern systems using nftables backend
        """
        return _disc.iptables_list()

    # --- Apply tools ---
    @mcp.tool()
    def set_sysctl(kv: dict[str, str]) -> dict:
        return _apply_sysctl.set_sysctl(kv)

    @mcp.tool()
    def apply_tc_script(lines: list[str]) -> dict:
        return _apply_tc.apply_tc_script(lines)

    @mcp.tool()
    def apply_nft_ruleset(ruleset: str) -> dict:
        return _apply_nft.apply_nft_ruleset(ruleset)

    @mcp.tool()
    def set_nic_offloads(iface: str, flags: dict[str, bool]) -> dict:
        return _apply_off.set_nic_offloads(iface, flags)

    @mcp.tool()
    def set_mtu(iface: str, mtu: int) -> dict:
        return _apply_mtu.set_mtu(iface, mtu)

