from fastmcp import FastMCP
from registry import register_tools, register_resources
from tools.util.policy_loader import PolicyRegistry
import json

# Global policy registry instance
policy_registry = PolicyRegistry(policy_root="policy/config_cards")

def main():
    mcp_server = FastMCP("MCP Network Optimizer")
    register_resources(mcp_server, policy_registry)
    register_tools(mcp_server)
    mcp_server.run()

if __name__ == "__main__":
    main()