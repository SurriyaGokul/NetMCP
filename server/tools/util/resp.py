def resp(ok: bool, code: int = 0, stdout: str = "", stderr: str = "") -> dict:
    return {"ok": ok, "code": code, "stdout": stdout, "stderr": stderr}
