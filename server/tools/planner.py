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
    
    # Render tc script
    if changes.qdisc or changes.shaper:
        rendered.tc_script = _render_tc(iface, changes.qdisc, changes.shaper)
    
    # Render nftables script for DSCP marking
    if changes.dscp:
        rendered.nft_script = _render_nft(iface, changes.dscp)
    
    # Render ethtool commands for offloads
    if changes.offloads:
        rendered.ethtool_cmds = _render_ethtool(iface, changes.offloads)
    
    # Render ip link commands for MTU
    if changes.mtu:
        rendered.ip_link_cmds = _render_ip_link(iface, changes.mtu)
    
    return rendered.model_dump()


def _render_sysctl(sysctl_set) -> list:
    """Render sysctl commands from a SysctlSet."""
    commands = []
    for key, value in sysctl_set.root.items():
        commands.append(f"sysctl -w {key}={value}")
    return commands


def _render_tc(iface: str, qdisc=None, shaper=None) -> str:
    """Render tc script for qdisc and shaper configuration."""
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
    
    return "\n".join(lines)


def _render_nft(iface: str, dscp_rules: list) -> str:
    """Render nftables script for DSCP marking."""
    lines = []
    
    lines.append("#!/usr/sbin/nft -f")
    lines.append("")
    lines.append("# Flush existing mangle table")
    lines.append("flush table ip mangle")
    lines.append("")
    lines.append("# Create mangle table and chains")
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
        dscp_value = dscp_map.get(dscp_name, "0")
        
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
    
    return "\n".join(lines)


def _render_ethtool(iface: str, offloads) -> list:
    """Render ethtool commands for offload settings."""
    commands = []
    
    offload_map = {
        "gro": "gro",
        "gso": "gso",
        "tso": "tso",
        "lro": "lro"
    }
    
    for field, ethtool_name in offload_map.items():
        value = getattr(offloads, field, None)
        if value is not None:
            state = "on" if value else "off"
            commands.append(f"ethtool -K {iface} {ethtool_name} {state}")
    
    return commands


def _render_ip_link(iface: str, mtu: int) -> list:
    """Render ip link command for MTU setting."""
    return [f"ip link set dev {iface} mtu {mtu}"]