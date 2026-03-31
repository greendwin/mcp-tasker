from tasker.parse import parse_task_file
from tasker.repo import TaskRepo

from ._common import get_repo, mcp
from ._model import TaskInfo, TaskPreview


def _list_root_previews(repo: TaskRepo) -> list[TaskPreview]:
    r: list[TaskPreview] = []
    for task_path in repo.list_root_tasks():
        task = parse_task_file(task_path).task
        r.append(TaskPreview.from_task(task))
    return r


def _load_task_info(repo: TaskRepo, ref: str) -> TaskInfo:
    task = repo.resolve_ref(ref)
    return TaskInfo.from_task(task)


@mcp.tool()
def list_tasks() -> list[TaskPreview]:
    """List all root tasks."""
    repo = get_repo()
    return _list_root_previews(repo)


@mcp.tool()
def view_task(task_ref: str) -> TaskInfo:
    """View detailed task info by its ID."""
    repo = get_repo()
    return _load_task_info(repo, task_ref)


@mcp.resource("task://index", mime_type="application/json")
def resource_task_index() -> list[TaskPreview]:
    """List all root tasks."""
    repo = get_repo()
    return _list_root_previews(repo)


@mcp.resource("task://{ref}", mime_type="application/json")
def resource_task(ref: str) -> TaskInfo:
    """View a task and its subtasks by reference."""
    repo = get_repo()
    return _load_task_info(repo, ref)
