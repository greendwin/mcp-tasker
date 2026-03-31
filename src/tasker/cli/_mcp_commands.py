import asyncio

from tasker.mcp import mcp

from ._common import app


@app.command("mcp", help="Start MCP server (stdio transport).")
def cmd_mcp() -> None:
    asyncio.run(mcp.run_stdio_async())
