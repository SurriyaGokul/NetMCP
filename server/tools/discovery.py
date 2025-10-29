from server.tools.util.shell import run
from server.tools.util.resp import resp

def ip_info() -> dict:
    """Display interfaces and addresses. (ip addr show) — No install.
    Returns: {ok, code, stdout, stderr}
    """
    try:
        r = run(["ip", "addr", "show"], timeout=5)
        return resp(**r)
    except Exception as e:
        return resp(False, 1, stderr=str(e))

def eth_info(iface: str = "eth0") -> dict:
    """Link speed/duplex/driver info. (ethtool <iface>) — No install.
    May require /usr/sbin in PATH.
    """
    try:
        return resp(**run(["ethtool", iface], timeout=5))
    except Exception as e:
        return resp(False, 1, stderr=str(e))

def nmcli_status() -> dict:
    """NetworkManager device status. (nmcli device status) — No install.
    May require NetworkManager installed.
    """
    try:
        return resp(**run(["nmcli", "device", "status"], timeout=5))
    except Exception as e:
        return resp(False, 1, stderr=str(e))

def iwconfig(iface: str = "wlan0") -> dict:
    """Wireless params. (iwconfig <iface>) — Maybe install (wireless-tools)."""
    try:
        return resp(**run(["iwconfig", iface], timeout=5))
    except Exception as e:
        return resp(False, 1, stderr=str(e))

def iwlist_scan(iface: str = "wlan0", subcmd: str = "scan") -> dict:
    """Wi‑Fi scan/list networks. (iwlist <iface> scan) — Maybe install (wireless-tools)."""
    try:
        return resp(**run(["iwlist", iface, subcmd], timeout=10))
    except Exception as e:
        return resp(False, 1, stderr=str(e))

def hostnamectl() -> dict:
    """Hostname + OS metadata. (hostnamectl status) — No install."""
    try:
        return resp(**run(["hostnamectl", "status"], timeout=5))
    except Exception as e:
        return resp(False, 1, stderr=str(e))

def arp_table() -> dict:
    """ARP table. (arp -n) — May require install (net-tools)."""
    try:
        return resp(**run(["arp", "-n"], timeout=5))
    except Exception as e:
        return resp(False, 1, stderr=str(e))

def ip_neigh() -> dict:
    """Neighbor cache (ARP/NDP). (ip neigh show) — No install."""
    try:
        return resp(**run(["ip", "neigh", "show"], timeout=5))
    except Exception as e:
        return resp(False, 1, stderr=str(e))

def ip_route() -> dict:
    """Routing table. (ip route show) — No install."""
    try:
        return resp(**run(["ip", "route", "show"], timeout=5))
    except Exception as e:
        return resp(False, 1, stderr=str(e))

def resolvectl_status() -> dict:
    """System DNS (systemd‑resolved). (resolvectl status) — Maybe install."""
    try:
        return resp(**run(["resolvectl", "status"], timeout=5))
    except Exception as e:
        return resp(False, 1, stderr=str(e))

def cat_resolv_conf() -> dict:
    """Show /etc/resolv.conf. — No install."""
    try:
        return resp(**run(["cat", "/etc/resolv.conf"], timeout=5))
    except Exception as e:
        return resp(False, 1, stderr=str(e))

def dig(domain: str, dns: str | None = None) -> dict:
    """DNS query. (dig [@dns] <domain>) — Maybe install (dnsutils/bind9-host)."""
    try:
        cmd = ["dig"]
        if dns:
            cmd += [f"@{dns}"]
        cmd += [domain]
        return resp(**run(cmd, timeout=5))
    except Exception as e:
        return resp(False, 1, stderr=str(e))

def host(domain: str) -> dict:
    """Simple DNS lookup. (host <domain>) — Maybe install (bind9-host)."""
    try:
        return resp(**run(["host", domain], timeout=5))
    except Exception as e:
        return resp(False, 1, stderr=str(e))

def nslookup(domain: str) -> dict:
    """Legacy DNS lookup. (nslookup <domain>) — Maybe install (dnsutils)."""
    try:
        return resp(**run(["nslookup", domain], timeout=5))
    except Exception as e:
        return resp(False, 1, stderr=str(e))

def ping_host(address: str, count: int = 3) -> dict:
    """ICMP echo test. (ping -c <count> <addr>) — No install."""
    try:
        return resp(**run(["ping", "-c", str(count), address], timeout=5 + count))
    except Exception as e:
        return resp(False, 1, stderr=str(e))

def traceroute(domain: str) -> dict:
    """Trace path. (traceroute <host>) — Maybe install."""
    try:
        return resp(**run(["traceroute", domain], timeout=20))
    except Exception as e:
        return resp(False, 1, stderr=str(e))

def tracepath(domain: str) -> dict:
    """Trace path without root. (tracepath <host>) — Maybe install."""
    try:
        return resp(**run(["tracepath", domain], timeout=20))
    except Exception as e:
        return resp(False, 1, stderr=str(e))

def ss_summary(options: str = "tulwn") -> dict:
    """Sockets & connections. (ss -<options>) — No install."""
    try:
        return resp(**run(["ss", f"-{options}"], timeout=5))
    except Exception as e:
        return resp(False, 1, stderr=str(e))

def tc_qdisc_show(iface: str) -> dict:
    """Show qdisc stats. (tc -s qdisc show dev <iface>) — No install."""
    try:
        return resp(**run(["tc", "-s", "qdisc", "show", "dev", iface], timeout=5))
    except Exception as e:
        return resp(False, 1, stderr=str(e))

def nft_list_ruleset() -> dict:
    """Show nftables rules. (nft list ruleset) — Maybe install (nftables)."""
    try:
        return resp(**run(["nft", "list", "ruleset"], timeout=5))
    except Exception as e:
        return resp(False, 1, stderr=str(e))

def iptables_list() -> dict:
    """Show iptables rules. (iptables -L -v -n) — Maybe install (iptables)."""
    try:
        return resp(**run(["iptables", "-L", "-v", "-n"], timeout=5))
    except Exception as e:
        return resp(False, 1, stderr=str(e))

def hostname_ips() -> dict:
    """Host IPs. (hostname -I) — No install."""
    try:
        return resp(**run(["hostname", "-I"], timeout=5))
    except Exception as e:
        return resp(False, 1, stderr=str(e))
