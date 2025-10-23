# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import subprocess
import yaml
import os
from typing import List

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

def run(cmd: List[str], timeout: int = 30) -> str:
    """
    Runs a command after checking if it is in the allowlist.

    Args:
        cmd: The command to run as a list of strings.
        timeout: The timeout in seconds.

    Returns:
        The stdout of the command as a string.

    Raises:
        ValueError: If the command is not in the allowlist.
        subprocess.CalledProcessError: If the command fails.
        subprocess.TimeoutExpired: If the command times out.
    """
    if not cmd or cmd[0] not in ALLOWED_BINARIES:
        raise ValueError(f"Command not allowed: {cmd[0]}")

    result = subprocess.run(
        cmd,
        check=True,
        capture_output=True,
        text=True,
        timeout=timeout
    )
    return result.stdout

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
    if not interpreter or interpreter[0] not in ALLOWED_BINARIES:
        raise ValueError(f"Interpreter not allowed: {interpreter[0]}")

    cmd = interpreter + [script]
    result = subprocess.run(
        cmd,
        check=True,
        capture_output=True,
        text=True,
        timeout=timeout
    )
    return result.stdout
