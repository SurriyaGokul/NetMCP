import subprocess
import yaml
import os
from typing import List

# Structured response helper
def _mk(ok: bool, code: int = 0, stdout: str = "", stderr: str = "") -> dict:
    return {"ok": ok, "code": code, "stdout": stdout, "stderr": stderr}

# Get the absolute path to the allowlist.yaml file
ALLOWLIST_PATH = os.path.join(os.path.dirname(__file__), '../../config/allowlist.yaml')

def get_allowlist() -> List[str]:
    """
    Reads the allowlist of binaries from the config file.
    """
    try:
        with open(ALLOWLIST_PATH, 'r') as f:
            config = yaml.safe_load(f)
            return config.get('binaries', [])
    except FileNotFoundError:
        return []

ALLOWED_BINARIES = get_allowlist()

def _reject_meta(args: List[str]) -> None:
    metas = {";", "&&", "||", "|", ">", "<", "`", "$(", ")"}
    if any(any(m in a for m in metas) for a in args):
        raise PermissionError("Unsafe metacharacter detected")

def run(cmd: List[str], timeout: int = 5) -> dict:
    """
    Run an allowlisted binary with strict args and timeout.
    Returns: dict { ok, code, stdout, stderr }
    """
    if not cmd:
        return _mk(False, 1, stderr="Empty command")

    # Allow either absolute allowed paths from config or bare binary names listed there
    binary = cmd[0]
    allowed = set(ALLOWED_BINARIES)
    allowed_names = {os.path.basename(p) for p in ALLOWED_BINARIES}
    if binary not in allowed and binary not in allowed_names:
        return _mk(False, 1, stderr=f"Command not allowlisted: {binary}")

    _reject_meta(cmd)
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
        return _mk(p.returncode == 0, p.returncode, p.stdout, p.stderr)
    except subprocess.TimeoutExpired as e:
        return _mk(False, 124, stderr=f"Timeout after {timeout}s")
    except FileNotFoundError as e:
        return _mk(False, 127, stderr=str(e))
    except Exception as e:
        return _mk(False, 1, stderr=str(e))

def run_privileged(cmd: List[str], timeout: int = 10) -> dict:
    """
    Run an allowlisted command with sudo (elevated privileges).
    Requires passwordless sudo to be configured for the specified commands.
    
    Use setup_sudo.sh to configure passwordless sudo for network commands.
    
    Args:
        cmd: Command to run as a list of strings
        timeout: Command timeout in seconds
    
    Returns:
        dict { ok, code, stdout, stderr }
    """
    if not cmd:
        return _mk(False, 1, stderr="Empty command")
    
    # Check if command is in allowlist
    binary = cmd[0]
    allowed = set(ALLOWED_BINARIES)
    allowed_names = {os.path.basename(p) for p in ALLOWED_BINARIES}
    if binary not in allowed and binary not in allowed_names:
        return _mk(False, 1, stderr=f"Command not allowlisted: {binary}")
    
    _reject_meta(cmd)
    
    # Prepend sudo -n (non-interactive)
    sudo_cmd = ["sudo", "-n"] + cmd
    
    try:
        p = subprocess.run(
            sudo_cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False
        )
        
        # Check for sudo password prompt (indicates sudo not configured)
        if p.returncode != 0 and "password" in p.stderr.lower():
            return _mk(
                False,
                p.returncode,
                stderr=f"Sudo requires password. Run setup_sudo.sh to configure passwordless sudo."
            )
        
        return _mk(p.returncode == 0, p.returncode, p.stdout, p.stderr)
    
    except subprocess.TimeoutExpired:
        return _mk(False, 124, stderr=f"Timeout after {timeout}s")
    except FileNotFoundError as e:
        return _mk(False, 127, stderr=f"sudo or {binary} not found: {e}")
    except Exception as e:
        return _mk(False, 1, stderr=str(e))


def is_sudo_configured() -> bool:
    """
    Check if passwordless sudo is configured for network commands.
    
    Returns:
        True if sudo is configured, False otherwise
    """
    # Test with a harmless command
    result = run_privileged(["sysctl", "--version"], timeout=2)
    return result.get("ok", False)


def run_script(script: str, interpreter: List[str], timeout: int = 30) -> str:
    """
    Runs a script using an interpreter after checking if the interpreter is in the allowlist.

    Args:
        script: The script to run as a string.
        interpreter: The interpreter to use as a list of strings (e.g., ['/bin/bash', '-c']).
        timeout: The timeout in seconds.

    Returns:
        The stdout of the script as a string.

    Raises:
        ValueError: If the interpreter is not in the allowlist.
        subprocess.CalledProcessError: If the script fails.
        subprocess.TimeoutExpired: If the script times out.
    """
    if not interpreter:
        raise ValueError("Missing interpreter")

    interp0 = interpreter[0]
    allowed = set(ALLOWED_BINARIES)
    allowed_names = {os.path.basename(p) for p in ALLOWED_BINARIES}
    if interp0 not in allowed and interp0 not in allowed_names:
        raise ValueError(f"Interpreter not allowlisted: {interp0}")

    cmd = interpreter + [script]
    result = subprocess.run(
        cmd,
        check=True,
        capture_output=True,
        text=True,
        timeout=timeout
    )
    return result.stdout
