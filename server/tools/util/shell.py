import subprocess
import yaml
import os
import sys
import getpass
from typing import List, Optional
from pathlib import Path

def _mk(ok: bool, code: int = 0, stdout: str = "", stderr: str = "") -> dict:
    return {"ok": ok, "code": code, "stdout": stdout, "stderr": stderr}

ALLOWLIST_PATH = os.path.join(os.path.dirname(__file__), '../../config/allowlist.yaml')

# Track if sudo has been authenticated this session
_sudo_authenticated = False
_sudo_cache_file = Path.home() / ".mcp-net-optimizer" / ".sudo_session"

def get_allowlist() -> List[str]:
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
    if not cmd:
        return _mk(False, 1, stderr="Empty command")

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


def check_sudo_access() -> dict:
    """
    Check if sudo access is available without requiring password.
    
    Returns:
        {
            "available": bool,
            "method": "passwordless" | "cached" | "none",
            "message": str
        }
    """
    # Try passwordless sudo first
    try:
        p = subprocess.run(
            ["sudo", "-n", "true"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if p.returncode == 0:
            return {
                "available": True,
                "method": "passwordless",
                "message": "Passwordless sudo is configured"
            }
    except Exception:
        pass
    
    # Check if sudo credentials are cached (from previous auth)
    try:
        p = subprocess.run(
            ["sudo", "-n", "-v"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if p.returncode == 0:
            return {
                "available": True,
                "method": "cached",
                "message": "Sudo credentials are cached from previous authentication"
            }
    except Exception:
        pass
    
    return {
        "available": False,
        "method": "none",
        "message": "Sudo requires password authentication. Call request_sudo_access() first."
    }


def request_sudo_access(password: Optional[str] = None) -> dict:
    """
    Request sudo access by validating credentials.
    This caches sudo credentials for the default timeout period (usually 15 minutes).
    
    Args:
        password: Optional password. If not provided in an interactive terminal,
                  will prompt for input. For non-interactive use, password must be provided.
    
    Returns:
        {
            "ok": bool,
            "message": str,
            "cache_timeout_minutes": int
        }
    """
    global _sudo_authenticated
    
    # First check if already configured for passwordless
    check = check_sudo_access()
    if check["available"]:
        _sudo_authenticated = True
        return {
            "ok": True,
            "message": check["message"],
            "cache_timeout_minutes": -1  # -1 means permanent/passwordless
        }
    
    # Need to authenticate with password
    if password:
        # Use provided password via stdin
        try:
            p = subprocess.run(
                ["sudo", "-S", "-v"],
                input=password + "\n",
                capture_output=True,
                text=True,
                timeout=10
            )
            if p.returncode == 0:
                _sudo_authenticated = True
                return {
                    "ok": True,
                    "message": "Sudo access granted. Credentials cached for ~15 minutes.",
                    "cache_timeout_minutes": 15
                }
            else:
                return {
                    "ok": False,
                    "message": f"Authentication failed: {p.stderr.strip()}",
                    "cache_timeout_minutes": 0
                }
        except subprocess.TimeoutExpired:
            return {
                "ok": False,
                "message": "Authentication timed out",
                "cache_timeout_minutes": 0
            }
        except Exception as e:
            return {
                "ok": False,
                "message": f"Authentication error: {str(e)}",
                "cache_timeout_minutes": 0
            }
    else:
        # No password provided - return instructions
        return {
            "ok": False,
            "message": "Password required. Provide password parameter or run setup_sudo.sh for permanent passwordless access.",
            "cache_timeout_minutes": 0,
            "options": [
                "1. Call request_sudo_access(password='your_password') to authenticate",
                "2. Run ./setup_sudo.sh to configure permanent passwordless sudo",
                "3. Manually run 'sudo -v' in terminal to cache credentials"
            ]
        }


def extend_sudo_cache() -> dict:
    """
    Extend the sudo credential cache timeout.
    Call this periodically to keep sudo access alive during long operations.
    
    Returns:
        {"ok": bool, "message": str}
    """
    try:
        p = subprocess.run(
            ["sudo", "-n", "-v"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if p.returncode == 0:
            return {"ok": True, "message": "Sudo cache extended"}
        else:
            return {"ok": False, "message": "Sudo cache expired. Re-authentication required."}
    except Exception as e:
        return {"ok": False, "message": f"Failed to extend cache: {str(e)}"}


def run_privileged(cmd: List[str], timeout: int = 10) -> dict:
    """
    Run a command with sudo privileges.
    
    This function will:
    1. First try passwordless sudo (-n flag)
    2. If that fails and credentials are cached, use them
    3. If no access, return helpful error with instructions
    
    Args:
        cmd: Command and arguments to run
        timeout: Command timeout in seconds
    
    Returns:
        Standard result dict with ok, code, stdout, stderr
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
    
    # Try with sudo -n (non-interactive, uses cached credentials or passwordless config)
    sudo_cmd = ["sudo", "-n"] + cmd
    
    try:
        p = subprocess.run(
            sudo_cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False
        )
        
        # Success
        if p.returncode == 0:
            return _mk(True, 0, p.stdout, p.stderr)
        
        # Check if it's a password issue vs command failure
        if "password" in p.stderr.lower() or "sudo:" in p.stderr.lower() and p.returncode == 1:
            # Sudo authentication issue
            return _mk(
                False,
                p.returncode,
                stderr=(
                    "Sudo access required but not available.\n"
                    "Options to resolve:\n"
                    "  1. Use the request_sudo_access tool with your password\n"
                    "  2. Run ./setup_sudo.sh for permanent passwordless access\n"
                    "  3. Run 'sudo -v' in your terminal to cache credentials"
                )
            )
        
        # Command ran but returned error (not auth issue)
        return _mk(False, p.returncode, p.stdout, p.stderr)
    
    except subprocess.TimeoutExpired:
        return _mk(False, 124, stderr=f"Timeout after {timeout}s")
    except FileNotFoundError as e:
        return _mk(False, 127, stderr=f"sudo or {binary} not found: {e}")
    except Exception as e:
        return _mk(False, 1, stderr=str(e))


def is_sudo_configured() -> bool:
    result = run_privileged(["sysctl", "--version"], timeout=2)
    return result.get("ok", False)


def run_script(script: str, interpreter: List[str], timeout: int = 30) -> str:
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
