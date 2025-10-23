from mcp.server.fastmcp import FastMCP
from registry import register_tools

def main():
    mcp_server = FastMCP()
    register_tools(mcp_server)
    mcp_server.run()


if __name__ == "__main__":
    main()