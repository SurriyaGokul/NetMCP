import builtins
import types
import pytest

# We'll import the modules after monkeypatching to keep isolation

from server.tools.util import shell
from server.tools.util.resp import resp


class DummyRun:
    def __init__(self, ok=True, code=0, stdout="", stderr=""):
        self.data = {"ok": ok, "code": code, "stdout": stdout, "stderr": stderr}
    def __call__(self, *args, **kwargs):
        return self.data


def test_ip_info_ok(monkeypatch):
    monkeypatch.setattr(shell, "run", DummyRun(stdout="ip ok\n"))
    from server.tools import discovery
    out = discovery.ip_info()
    assert out["ok"] is True
    assert "ip ok" in out["stdout"]


def test_eth_info_missing_bin(monkeypatch):
    # Simulate allowlist rejection
    def fake_run(cmd, timeout=5):
        return {"ok": False, "code": 1, "stdout": "", "stderr": "Command not allowlisted: ethtool"}
    monkeypatch.setattr(shell, "run", fake_run)
    from server.tools import discovery
    out = discovery.eth_info("ethX")
    assert out["ok"] is False
    assert "allowlisted" in out["stderr"]


def test_ping_host_count(monkeypatch):
    # Ensure count is passed; we just check that run is called with -c <count>
    calls = {}
    def fake_run(cmd, timeout):
        calls["cmd"] = cmd
        return {"ok": True, "code": 0, "stdout": "pong\n", "stderr": ""}
    monkeypatch.setattr(shell, "run", fake_run)
    from server.tools import discovery
    out = discovery.ping_host("1.1.1.1", count=2)
    assert out["ok"] is True
    assert calls["cmd"][0] == "ping"
    assert calls["cmd"][1] == "-c"
    assert calls["cmd"][2] == "2"


def test_set_sysctl_happy(monkeypatch):
    outputs = []
    def fake_run(cmd, timeout):
        outputs.append(cmd)
        return {"ok": True, "code": 0, "stdout": f"{cmd[-1]}\n", "stderr": ""}
    monkeypatch.setattr(shell, "run", fake_run)
    from server.tools.apply import sysctl as apply_sysctl
    out = apply_sysctl.set_sysctl({"net.ipv4.ip_forward": "1", "net.core.rmem_max": "262144"})
    assert out["ok"] is True
    assert "net.ipv4.ip_forward=1" in out["stdout"]
    assert outputs[0][0] == "sysctl"


def test_apply_nft_ruleset_check_fails(monkeypatch, tmp_path):
    # First nft -c fails
    calls = []
    def fake_run(cmd, timeout):
        calls.append(list(cmd))
        if "-c" in cmd:
            return {"ok": False, "code": 1, "stdout": "", "stderr": "syntax error"}
        return {"ok": True, "code": 0, "stdout": "ok\n", "stderr": ""}
    monkeypatch.setattr(shell, "run", fake_run)
    from server.tools.apply import nft as apply_nft
    out = apply_nft.apply_nft_ruleset("table ip filter {}")
    assert out["ok"] is False
    assert "syntax error" in out["stderr"]
