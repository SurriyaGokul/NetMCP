from server.tools.util.shell import run
from server.tools.util.resp import resp

def apply_tc_script(lines: list[str]) -> dict:
	"""
	Apply tc commands deterministically.
	lines: e.g., ["tc qdisc replace dev eth0 root cake bandwidth 90mbit diffserv ecn"]
	Returns: {ok, code, stdout, stderr}
	"""
	try:
		outputs: list[str] = []
		for line in lines:
			parts = line.split()
			if not parts:
				continue
			r = run(parts, timeout=5)
			outputs.append(r.get("stdout", ""))
			if not r.get("ok"):
				return resp(False, r.get("code", 1), stdout="".join(outputs), stderr=r.get("stderr", ""))
		return resp(True, 0, stdout="".join(outputs))
	except Exception as e:
		return resp(False, 1, stderr=str(e))
