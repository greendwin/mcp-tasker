from mcp.server.fastmcp import FastMCP

mcp = FastMCP("tasker")


@mcp.tool()
def hello() -> str:
    """Say hello from tasker MCP server."""
    return "Hello from tasker!"
