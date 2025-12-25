from fastmcp import FastMCP
import json
import os
import sys
from pathlib import Path

# Handle both direct execution and module execution
SERVER_DIR = Path(__file__).parent
PROJECT_ROOT = SERVER_DIR.parent

# Add project root to path for direct execution (FastMCP Cloud)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Use absolute imports that work in both contexts
from server.registry import register_tools, register_resources
from server.tools.util.policy_loader import PolicyRegistry

POLICY_ROOT = PROJECT_ROOT / "policy" / "config_cards"

policy_registry = PolicyRegistry(policy_root=str(POLICY_ROOT))

# Create server at module level with standard name for FastMCP Cloud discovery
mcp = FastMCP("MCP Network Optimizer")
register_resources(mcp, policy_registry)
register_tools(mcp)

def main():
    mcp.run()

if __name__ == "__main__":
    main()