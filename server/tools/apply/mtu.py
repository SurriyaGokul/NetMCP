from server.tools.util.shell import run
from server.tools.util.resp import resp

def set_mtu(iface: str, mtu: int) -> dict:
	"""Set interface MTU. Example: 1500
	Returns: {ok, code, stdout, stderr}
	"""
	try:
		return resp(**run(["ip", "link", "set", "dev", iface, "mtu", str(mtu)], timeout=5))
	except Exception as e:
		return resp(False, 1, stderr=str(e))
