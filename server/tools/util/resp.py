def resp(ok: bool, code: int = 0, stdout: str = "", stderr: str = "") -> dict:
    """Standard tool response shape.

    Returns a dict with keys: ok, code, stdout, stderr
    """
    return {"ok": ok, "code": code, "stdout": stdout, "stderr": stderr}
