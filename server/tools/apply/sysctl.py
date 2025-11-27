from server.tools.util.shell import run
from server.tools.util.resp import resp

def set_sysctl(kv: dict[str, str]) -> dict:
	try:
		outputs: list[str] = []
		for k, v in sorted(kv.items()):={v}"], timeout=5)
			outputs.append(r.get("stdout", ""))
			if not r.get("ok"):
				return resp(False, r.get("code", 1), stdout="".join(outputs), stderr=r.get("stderr", ""))
		return resp(True, 0, stdout="".join(outputs))
	except Exception as e:
		return resp(False, 1, stderr=str(e))
