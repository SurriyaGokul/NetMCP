from server.tools.util.shell import run
from server.tools.util.resp import resp

def set_nic_offloads(iface: str, flags: dict[str, bool]) -> dict:
	"""Toggle GRO/GSO/TSO/LRO. Example: {"gro": False, "tso": False}
	Returns: {ok, code, stdout, stderr}
	"""
	try:
		outputs: list[str] = []
		for k in ["gro", "gso", "tso", "lro"]:
			if k in flags:
				r = run(["ethtool", "-K", iface, k, "on" if flags[k] else "off"], timeout=5)
				outputs.append(r.get("stdout", ""))
				if not r.get("ok"):
					return resp(False, r.get("code", 1), stdout="".join(outputs), stderr=r.get("stderr", ""))
		return resp(True, 0, stdout="".join(outputs))
	except Exception as e:
		return resp(False, 1, stderr=str(e))
