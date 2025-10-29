from server.tools.util.shell import run
from server.tools.util.resp import resp
import tempfile, os

def apply_nft_ruleset(ruleset: str) -> dict:
	"""Atomically apply nftables ruleset; pre-check with -c.
	Returns: {ok, code, stdout, stderr}
	"""
	try:
		with tempfile.NamedTemporaryFile("w", delete=False) as f:
			f.write(ruleset)
			path = f.name
		chk = run(["nft", "-c", "-f", path], timeout=5)
		if not chk.get("ok"):
			os.unlink(path)
			return resp(False, chk.get("code", 1), stderr=chk.get("stderr", ""))
		ap = run(["nft", "-f", path], timeout=5)
		os.unlink(path)
		return resp(**ap)
	except Exception as e:
		return resp(False, 1, stderr=str(e))
