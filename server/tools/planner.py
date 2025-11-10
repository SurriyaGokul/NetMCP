def render_change_plan(plan: dict) -> dict:
    """
    Render a ParameterPlan into concrete command lists/scripts.
    This function does not produce side effects.

    Args:
        plan (dict): The ParameterPlan to be rendered.

    Returns:
        dict: A RenderedPlan dictionary containing the rendered commands/scripts.
    """
    from ..schema.models import ParameterPlan, RenderedPlan
    
    # Validate and parse the input plan
    try:
        param_plan = ParameterPlan(**plan)
    except Exception as e:
        raise ValueError(f"Invalid ParameterPlan: {e}")
    
    # Initialize the rendered plan structure
    rendered = RenderedPlan()
    
    iface = param_plan.iface
    changes = param_plan.changes
    
    # Render sysctl commands
    if changes.sysctl:
        rendered.sysctl_cmds = _render_sysctl(changes.sysctl)
    
    # Render tc script (includes qdisc, shaper, netem, htb_classes)
    if changes.qdisc or changes.shaper or changes.netem or changes.htb_classes:
        rendered.tc_script = _render_tc(
            iface, 
            changes.qdisc, 
            changes.shaper, 
            changes.netem,
            changes.htb_classes
        )
    
    # Render nftables script for DSCP marking, connection limits, rate limits, NAT
    nft_sections = []
    if changes.dscp:
        nft_sections.append(("dscp", changes.dscp))
    if changes.connection_limits:
        nft_sections.append(("connection_limits", changes.connection_limits))
    if changes.rate_limits:
        nft_sections.append(("rate_limits", changes.rate_limits))
    if changes.nat_rules:
        nft_sections.append(("nat", changes.nat_rules))
    
    if nft_sections:
        rendered.nft_script = _render_nft(iface, nft_sections)
    
    # Handle connection tracking via sysctl
    if changes.connection_tracking:
        tracking_sysctls = _render_connection_tracking(changes.connection_tracking)
        if not rendered.sysctl_cmds:
            rendered.sysctl_cmds = []
        rendered.sysctl_cmds.extend(tracking_sysctls)
    
    return rendered.model_dump()


def _render_sysctl(sysctl_set) -> list:
    """Render sysctl commands from a SysctlSet."""
    commands = []
    for key, value in sysctl_set.root.items():
        commands.append(f"sysctl -w {key}={value}")
    return commands


def _render_tc(iface: str, qdisc=None, shaper=None, netem=None, htb_classes=None) -> str:
    """Render tc script for qdisc, shaper, netem, and HTB class configuration."""
    lines = []
    
    # Delete existing qdiscs first
    lines.append(f"# Clear existing qdisc on {iface}")
    lines.append(f"tc qdisc del dev {iface} root 2>/dev/null || true")
    lines.append("")
    
    if qdisc:
        qdisc_type = qdisc.type
        params = qdisc.params
        
        if qdisc_type == "htb":
            # HTB setup with classes
            lines.append(f"# Setup HTB qdisc on {iface}")
            lines.append(f"tc qdisc add dev {iface} root handle 1: htb default 30")
            
            # Root class
            if shaper:
                if shaper.egress_mbit:
                    rate = f"{shaper.egress_mbit}mbit"
                    ceil = f"{shaper.ceil_mbit}mbit" if shaper.ceil_mbit else rate
                    lines.append(f"tc class add dev {iface} parent 1: classid 1:1 htb rate {rate} ceil {ceil}")
                    
                    # Default class
                    lines.append(f"tc class add dev {iface} parent 1:1 classid 1:30 htb rate {rate} ceil {ceil}")
            else:
                lines.append(f"tc class add dev {iface} parent 1: classid 1:1 htb rate 1gbit")
                lines.append(f"tc class add dev {iface} parent 1:1 classid 1:30 htb rate 1gbit")
            
            # Add custom HTB classes
            if htb_classes:
                lines.append("")
                lines.append("# Custom HTB classes")
                for htb_class in htb_classes:
                    classid = htb_class.classid
                    rate = f"{htb_class.rate_mbit}mbit"
                    ceil = f"{htb_class.ceil_mbit}mbit" if htb_class.ceil_mbit else rate
                    priority = htb_class.priority if htb_class.priority is not None else 3
                    
                    cmd_parts = [
                        f"tc class add dev {iface} parent 1:1 classid {classid}",
                        f"htb rate {rate} ceil {ceil} prio {priority}"
                    ]
                    
                    if htb_class.burst:
                        cmd_parts.append(f"burst {htb_class.burst}")
                    
                    lines.append(" ".join(cmd_parts))
        
        elif qdisc_type == "cake":
            # CAKE qdisc
            lines.append(f"# Setup CAKE qdisc on {iface}")
            cmd_parts = [f"tc qdisc add dev {iface} root cake"]
            
            if shaper and shaper.egress_mbit:
                cmd_parts.append(f"bandwidth {shaper.egress_mbit}mbit")
            
            # Add any additional CAKE parameters
            for key, value in params.items():
                if key == "rtt":
                    cmd_parts.append(f"rtt {value}")
                elif key == "diffserv":
                    cmd_parts.append(f"diffserv{value}")
            
            lines.append(" ".join(cmd_parts))
        
        elif qdisc_type == "fq_codel":
            # FQ-CoDel qdisc
            lines.append(f"# Setup FQ-CoDel qdisc on {iface}")
            cmd_parts = [f"tc qdisc add dev {iface} root fq_codel"]
            
            # Add FQ-CoDel parameters
            for key, value in params.items():
                if key == "limit":
                    cmd_parts.append(f"limit {value}")
                elif key == "target":
                    cmd_parts.append(f"target {value}")
                elif key == "interval":
                    cmd_parts.append(f"interval {value}")
            
            lines.append(" ".join(cmd_parts))
        
        elif qdisc_type == "fq":
            # Fair Queue qdisc
            lines.append(f"# Setup FQ qdisc on {iface}")
            cmd_parts = [f"tc qdisc add dev {iface} root fq"]
            
            # Add FQ parameters if any
            for key, value in params.items():
                if key == "pacing":
                    cmd_parts.append(f"pacing")
                elif key == "maxrate":
                    cmd_parts.append(f"maxrate {value}")
            
            lines.append(" ".join(cmd_parts))
        
        elif qdisc_type == "pfifo_fast":
            # Default Linux qdisc
            lines.append(f"# Setup pfifo_fast qdisc on {iface}")
            lines.append(f"tc qdisc add dev {iface} root pfifo_fast")
    
    # Add netem for network emulation (delay, loss, etc.)
    if netem:
        lines.append("")
        lines.append(f"# Add netem for network emulation on {iface}")
        
        # If we have a root qdisc, add netem as a child
        # Otherwise, add it as root
        parent = "parent 1:30" if qdisc and qdisc.type == "htb" else "root"
        
        netem_parts = [f"tc qdisc add dev {iface} {parent} netem"]
        
        if netem.delay_ms is not None:
            delay_str = f"{netem.delay_ms}ms"
            if netem.delay_jitter_ms:
                delay_str += f" {netem.delay_jitter_ms}ms"
            netem_parts.append(f"delay {delay_str}")
        
        if netem.loss_pct is not None:
            netem_parts.append(f"loss {netem.loss_pct}%")
        
        if netem.duplicate_pct is not None:
            netem_parts.append(f"duplicate {netem.duplicate_pct}%")
        
        if netem.corrupt_pct is not None:
            netem_parts.append(f"corrupt {netem.corrupt_pct}%")
        
        if netem.reorder_pct is not None:
            netem_parts.append(f"reorder {netem.reorder_pct}%")
        
        lines.append(" ".join(netem_parts))
    
    return "\n".join(lines)


def _render_nft(iface: str, sections: list) -> str:
    """Render comprehensive nftables script for DSCP, connection limits, rate limits, and NAT."""
    lines = []
    
    lines.append("#!/usr/sbin/nft -f")
    lines.append("")
    
    # Process each section type
    has_filter = False
    has_nat = False
    has_mangle = False
    
    dscp_rules = None
    connection_limits = None
    rate_limits = None
    nat_rules = None
    
    for section_type, section_data in sections:
        if section_type == "dscp":
            dscp_rules = section_data
            has_mangle = True
        elif section_type == "connection_limits":
            connection_limits = section_data
            has_filter = True
        elif section_type == "rate_limits":
            rate_limits = section_data
            has_filter = True
        elif section_type == "nat":
            nat_rules = section_data
            has_nat = True
    
    # Render filter table (connection limits, rate limits)
    if has_filter:
        lines.append("# Filter table for connection and rate limiting")
        lines.append("table inet filter {")
        
        if connection_limits or rate_limits:
            lines.append("  chain input {")
            lines.append("    type filter hook input priority 0; policy accept;")
            lines.append("")
            
            # Connection limiting rules
            if connection_limits:
                lines.append("    # Connection limiting rules")
                for limit_rule in connection_limits:
                    protocol = limit_rule.protocol
                    port = limit_rule.port
                    limit = limit_rule.limit
                    mask = limit_rule.mask if limit_rule.mask else 32
                    
                    if mask == 32:
                        lines.append(
                            f"    {protocol} dport {port} ct state new "
                            f"add @connlimit_{{ip saddr}} {{ ip saddr ct count over {limit} }} drop"
                        )
                    else:
                        # Subnet-based limiting (simplified for /24)
                        lines.append(
                            f"    {protocol} dport {port} ct state new "
                            f"meter connlimit_{port} {{ ip saddr & 255.255.255.0 ct count over {limit} }} drop"
                        )
                lines.append("")
            
            # Rate limiting rules
            if rate_limits:
                lines.append("    # Rate limiting rules")
                for rate_rule in rate_limits:
                    rate = rate_rule.rate
                    burst = rate_rule.burst if rate_rule.burst else 10
                    
                    # Parse rate (e.g., "150/second")
                    rate_parts = rate.split("/")
                    if len(rate_parts) == 2:
                        rate_value = rate_parts[0]
                        rate_unit = rate_parts[1]
                        lines.append(
                            f"    limit rate over {rate_value}/{rate_unit} burst {burst} packets drop"
                        )
                lines.append("")
            
            lines.append("  }")
        
        lines.append("}")
        lines.append("")
    
    # Render mangle table (DSCP marking)
    if has_mangle and dscp_rules:
        lines.append("# Mangle table for DSCP marking")
        lines.append("table ip mangle {")
        lines.append("  chain postrouting {")
        lines.append("    type filter hook postrouting priority -150; policy accept;")
        lines.append("")
        
        # DSCP value mapping
        dscp_map = {
            "EF": "46",
            "CS6": "48",
            "CS5": "40",
            "CS4": "32",
            "AF41": "34",
            "AF42": "36",
            "AF43": "38"
        }
        
        for rule in dscp_rules:
            match = rule.match
            dscp_name = rule.dscp
            
            # Build match criteria
            match_parts = []
            
            if match.proto:
                match_parts.append(f"meta l4proto {match.proto}")
            
            if match.src:
                match_parts.append(f"ip saddr {match.src}")
            
            if match.dst:
                match_parts.append(f"ip daddr {match.dst}")
            
            if match.sports:
                if len(match.sports) == 1:
                    match_parts.append(f"{match.proto} sport {match.sports[0]}")
                else:
                    sport_range = f"{{{','.join(map(str, match.sports))}}}"
                    match_parts.append(f"{match.proto} sport {sport_range}")
            
            if match.dports:
                if len(match.dports) == 1:
                    match_parts.append(f"{match.proto} dport {match.dports[0]}")
                else:
                    dport_range = f"{{{','.join(map(str, match.dports))}}}"
                    match_parts.append(f"{match.proto} dport {dport_range}")
            
            match_str = " ".join(match_parts)
            lines.append(f"    {match_str} ip dscp set {dscp_name.lower()} counter")
        
        lines.append("  }")
        lines.append("}")
        lines.append("")
    
    # Render NAT table
    if has_nat and nat_rules:
        lines.append("# NAT table")
        lines.append("table ip nat {")
        lines.append("  chain postrouting {")
        lines.append("    type nat hook postrouting priority 100; policy accept;")
        lines.append("")
        
        for nat_rule in nat_rules:
            nat_type = nat_rule.type
            rule_iface = nat_rule.iface
            to_addr = nat_rule.to_addr
            to_port = nat_rule.to_port
            
            if nat_type == "masquerade" and rule_iface:
                lines.append(f"    oifname {rule_iface} masquerade")
            elif nat_type == "snat" and to_addr:
                if rule_iface:
                    lines.append(f"    oifname {rule_iface} snat to {to_addr}")
                else:
                    lines.append(f"    snat to {to_addr}")
            elif nat_type == "dnat" and to_addr:
                dnat_target = f"{to_addr}:{to_port}" if to_port else to_addr
                lines.append(f"    dnat to {dnat_target}")
        
        lines.append("  }")
        lines.append("}")
    
    return "\n".join(lines)


def _render_connection_tracking(tracking) -> list:
    """Render sysctl commands for connection tracking configuration."""
    commands = []
    
    if tracking.max_connections:
        commands.append(f"sysctl -w net.netfilter.nf_conntrack_max={tracking.max_connections}")
    
    if tracking.tcp_timeout_established:
        commands.append(
            f"sysctl -w net.netfilter.nf_conntrack_tcp_timeout_established={tracking.tcp_timeout_established}"
        )
    
    if tracking.tcp_timeout_close_wait:
        commands.append(
            f"sysctl -w net.netfilter.nf_conntrack_tcp_timeout_close_wait={tracking.tcp_timeout_close_wait}"
        )
    
    return commands


# --- Helper renderers for MCP Tools integration ---
def render_sysctl(kv: dict[str, str]) -> list[str]:
    """Render sysctl -w lines in deterministic order."""
    return [f"sysctl -w {k}={v}" for k, v in sorted(kv.items())]

def render_cake_root(iface: str, bandwidth_mbit: int, diffserv: bool = True, ecn: bool = True) -> list[str]:
    """Render a single CAKE root qdisc line for tc."""
    parts = ["tc", "qdisc", "replace", "dev", iface, "root", "cake", "bandwidth", f"{bandwidth_mbit}mbit"]
    if diffserv:
        parts.append("diffserv")
    if ecn:
        parts.append("ecn")
    return [" ".join(parts)]