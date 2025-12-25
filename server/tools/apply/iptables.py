from server.tools.util.shell import run
from server.tools.util.resp import resp

def apply_connection_limits(limits: list[dict]) -> dict:
	"""
	Apply connection limiting rules using nftables.
	
	Args:
		limits: List of connection limit rules with protocol, port, limit, and mask
	
	Returns:
		{ok, code, stdout, stderr}
	"""
	try:
		# Build nftables script for connection limiting
		script_lines = ["#!/usr/sbin/nft -f", ""]
		
		# Create or flush filter table
		script_lines.append("table inet filter {")
		script_lines.append("  chain input {")
		script_lines.append("    type filter hook input priority 0; policy accept;")
		script_lines.append("")
		
		for limit_rule in limits:
			protocol = limit_rule.get("protocol", "tcp")
			port = limit_rule.get("port")
			limit = limit_rule.get("limit", 20)
			mask = limit_rule.get("mask", 32)
			
			# Add connection limiting rule
			if mask == 32:
				# Per-IP limiting
				script_lines.append(
					f"    {protocol} dport {port} ct state new "
					f"add @connlimit_{{ip saddr}} {{ ip saddr ct count over {limit} }} drop"
				)
			else:
				# Per-subnet limiting
				script_lines.append(
					f"    {protocol} dport {port} ct state new "
					f"add @connlimit_{{ip saddr & 255.255.255.0}} {{ ip saddr & 255.255.255.0 ct count over {limit} }} drop"
				)
		
		script_lines.append("  }")
		script_lines.append("}")
		
		script = "\n".join(script_lines)
		
		# Apply via nft module
		from server.tools.apply import nft as apply_nft
		return apply_nft.apply_nft_ruleset(script)
		
	except Exception as e:
		return resp(False, 1, stderr=str(e))


def apply_rate_limits(limits: list[dict]) -> dict:
	try:
		script_lines = ["#!/usr/sbin/nft -f", ""]
		
		script_lines.append("table inet filter {")
		script_lines.append("  chain input {")
		script_lines.append("    type filter hook input priority 0; policy accept;")
		script_lines.append("")
		
		for rate_rule in limits:
			rate = rate_rule.get("rate", "150/second")
			burst = rate_rule.get("burst", 10)
			
			# Parse rate (e.g., "150/second" -> "150 per second")
			rate_parts = rate.split("/")
			if len(rate_parts) == 2:
				rate_value = rate_parts[0]
				rate_unit = rate_parts[1]
				script_lines.append(
					f"    limit rate over {rate_value}/{rate_unit} burst {burst} packets drop"
				)
		
		script_lines.append("  }")
		script_lines.append("}")
		
		script = "\n".join(script_lines)
		
		from server.tools.apply import nft as apply_nft
		return apply_nft.apply_nft_ruleset(script)
		
	except Exception as e:
		return resp(False, 1, stderr=str(e))


def apply_connection_tracking(tracking: dict) -> dict:
	try:
		sysctl_params = {}
		
		if "max_connections" in tracking:
			sysctl_params["net.netfilter.nf_conntrack_max"] = str(tracking["max_connections"])
		
		if "tcp_timeout_established" in tracking:
			sysctl_params["net.netfilter.nf_conntrack_tcp_timeout_established"] = str(
				tracking["tcp_timeout_established"]
			)
		
		if "tcp_timeout_close_wait" in tracking:
			sysctl_params["net.netfilter.nf_conntrack_tcp_timeout_close_wait"] = str(
				tracking["tcp_timeout_close_wait"]
			)
		
		# Apply via sysctl module
		from server.tools.apply import sysctl as apply_sysctl
		return apply_sysctl.set_sysctl(sysctl_params)
		
	except Exception as e:
		return resp(False, 1, stderr=str(e))


def apply_nat_rules(nat_rules: list[dict]) -> dict:
	try:
		script_lines = ["#!/usr/sbin/nft -f", ""]
		
		script_lines.append("table ip nat {")
		script_lines.append("  chain postrouting {")
		script_lines.append("    type nat hook postrouting priority 100; policy accept;")
		script_lines.append("")
		
		for nat_rule in nat_rules:
			nat_type = nat_rule.get("type", "masquerade")
			iface = nat_rule.get("iface")
			to_addr = nat_rule.get("to_addr")
			to_port = nat_rule.get("to_port")
			
			if nat_type == "masquerade" and iface:
				script_lines.append(f"    oifname {iface} masquerade")
			elif nat_type == "snat" and to_addr:
				if iface:
					script_lines.append(f"    oifname {iface} snat to {to_addr}")
				else:
					script_lines.append(f"    snat to {to_addr}")
			elif nat_type == "dnat" and to_addr:
				script_lines.append(f"    dnat to {to_addr}")
		
		script_lines.append("  }")
		script_lines.append("}")
		
		script = "\n".join(script_lines)
		
		from server.tools.apply import nft as apply_nft
		return apply_nft.apply_nft_ruleset(script)
		
	except Exception as e:
		return resp(False, 1, stderr=str(e))
