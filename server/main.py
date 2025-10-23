from fastmcp import FastMCP
from registry import register_tools
from tools.util.policy_loader import PolicyRegistry

def main():
    mcp_server = FastMCP("MCP Network Optimizer")
    
    # Initialize PolicyRegistry and store in server state
    policy_registry = PolicyRegistry(policy_root="policy/config_cards")
    mcp_server.state["policy"] = policy_registry
    
    # Register tools with access to server state
    register_tools(mcp_server)
    
    mcp_server.run()


if __name__ == "__main__":
    main()