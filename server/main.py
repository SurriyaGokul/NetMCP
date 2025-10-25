from fastmcp import FastMCP
from .registry import register_tools, register_resources
from .tools.util.policy_loader import PolicyRegistry
import json
import os
from pathlib import Path

# Get the project root directory (parent of server directory)
SERVER_DIR = Path(__file__).parent
PROJECT_ROOT = SERVER_DIR.parent
POLICY_ROOT = PROJECT_ROOT / "policy" / "config_cards"

# Global policy registry instance
policy_registry = PolicyRegistry(policy_root=str(POLICY_ROOT))

def main():
    mcp_server = FastMCP("MCP Network Optimizer")
    register_resources(mcp_server, policy_registry)
    register_tools(mcp_server)
    mcp_server.run()

if __name__ == "__main__":
    main()