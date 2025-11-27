from server.tools.util.shell import run
from server.tools.util.resp import resp

def ip_info() -> dict:
    try:
        r = run(["ip", "addr", "show"], timeout=5)
        return resp(**r)
    except Exception as e:
        return resp(False, 1, stderr=str(e))

def eth_info(iface: str = "eth0") -> dict:
    try:
        return resp(**run(["ethtool", iface], timeout=5))
    except Exception as e:
        return resp(False, 1, stderr=str(e))

def nmcli_status() -> dict:
    try:
        return resp(**run(["nmcli", "device", "status"], timeout=5))
    except Exception as e:
        return resp(False, 1, stderr=str(e))

def iwconfig(iface: str = "wlan0") -> dict:
    try:
        return resp(**run(["iwconfig", iface], timeout=5))
    except Exception as e:
        return resp(False, 1, stderr=str(e))

def iwlist_scan(iface: str = "wlan0", subcmd: str = "scan") -> dict:
    try:
        return resp(**run(["iwlist", iface, subcmd], timeout=10))
    except Exception as e:
        return resp(False, 1, stderr=str(e))

def hostnamectl() -> dict:
    try:
        return resp(**run(["hostnamectl", "status"], timeout=5))
    except Exception as e:
        return resp(False, 1, stderr=str(e))

def arp_table() -> dict:
    try:
        return resp(**run(["arp", "-n"], timeout=5))
    except Exception as e:
        return resp(False, 1, stderr=str(e))

def ip_neigh() -> dict:
    try:
        return resp(**run(["ip", "neigh", "show"], timeout=5))
    except Exception as e:
        return resp(False, 1, stderr=str(e))

def ip_route() -> dict:
    try:
        return resp(**run(["ip", "route", "show"], timeout=5))
    except Exception as e:
        return resp(False, 1, stderr=str(e))

def resolvectl_status() -> dict:
    try:
        return resp(**run(["resolvectl", "status"], timeout=5))
    except Exception as e:
        return resp(False, 1, stderr=str(e))

def cat_resolv_conf() -> dict:
    try:
        return resp(**run(["cat", "/etc/resolv.conf"], timeout=5))
    except Exception as e:
        return resp(False, 1, stderr=str(e))

def dig(domain: str, dns: str | None = None) -> dict:
    try:
        cmd = ["dig"]
        if dns:
            cmd += [f"@{dns}"]
        cmd += [domain]
        return resp(**run(cmd, timeout=5))
    except Exception as e:
        return resp(False, 1, stderr=str(e))

def host(domain: str) -> dict:
    try:
        return resp(**run(["host", domain], timeout=5))
    except Exception as e:
        return resp(False, 1, stderr=str(e))

def nslookup(domain: str) -> dict:
    try:
        return resp(**run(["nslookup", domain], timeout=5))
    except Exception as e:
        return resp(False, 1, stderr=str(e))

def ping_host(address: str, count: int = 3) -> dict:
    try:
        return resp(**run(["ping", "-c", str(count), address], timeout=5 + count))
    except Exception as e:
        return resp(False, 1, stderr=str(e))

def traceroute(domain: str) -> dict:
    try:
        return resp(**run(["traceroute", domain], timeout=20))
    except Exception as e:
        return resp(False, 1, stderr=str(e))

def tracepath(domain: str) -> dict:
    try:
        return resp(**run(["tracepath", domain], timeout=20))
    except Exception as e:
        return resp(False, 1, stderr=str(e))

def ss_summary(options: str = "tulwn") -> dict:
    try:
        return resp(**run(["ss", f"-{options}"], timeout=5))
    except Exception as e:
        return resp(False, 1, stderr=str(e))

def tc_qdisc_show(iface: str) -> dict:
    try:
        return resp(**run(["tc", "-s", "qdisc", "show", "dev", iface], timeout=5))
    except Exception as e:
        return resp(False, 1, stderr=str(e))

def nft_list_ruleset() -> dict:
    try:
        return resp(**run(["nft", "list", "ruleset"], timeout=5))
    except Exception as e:
        return resp(False, 1, stderr=str(e))

def iptables_list() -> dict:
    try:
        return resp(**run(["iptables", "-L", "-v", "-n"], timeout=5))
    except Exception as e:
        return resp(False, 1, stderr=str(e))

def hostname_ips() -> dict:
    try:
        return resp(**run(["hostname", "-I"], timeout=5))
    except Exception as e:
        return resp(False, 1, stderr=str(e))
