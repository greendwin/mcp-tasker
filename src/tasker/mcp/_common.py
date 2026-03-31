from pathlib import Path

from mcp.server.fastmcp import FastMCP

from tasker.repo import TaskRepo

mcp = FastMCP("tasker")


def get_repo() -> TaskRepo:
    tasker_dir = Path("tasker")

    # TODO: we must search for `tasker` directory, not create it
    tasker_dir.mkdir(exist_ok=True)
    return TaskRepo(tasker_dir)
