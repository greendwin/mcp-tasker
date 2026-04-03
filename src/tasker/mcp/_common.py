from mcp.server.fastmcp import FastMCP

from tasker.layout import discover_tasker_dir
from tasker.repo import TaskRepo

mcp = FastMCP("tasker")


def get_repo() -> TaskRepo:
    tasker_dir = discover_tasker_dir()
    return TaskRepo(tasker_dir)
