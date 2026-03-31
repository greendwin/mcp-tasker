import asyncio
from typing import Annotated

import typer

from tasker.mcp import mcp

from ._common import app


@app.command(
    "mcp", help="Start MCP server (stdio transport, or HTTP if --port is given)."
)
def cmd_mcp(
    port: Annotated[
        int | None,
        typer.Option("--port", help="Port to listen on (starts HTTP/SSE server)."),
    ] = None,
) -> None:
    if port is None:
        asyncio.run(mcp.run_stdio_async())
        return

    mcp.settings.port = port
    asyncio.run(mcp.run_streamable_http_async())
