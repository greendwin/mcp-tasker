from tasker.parse import parse_task_file
from tasker.repo import TaskRepo
from tasker.resolve import resolve_ref
from tasker.todo import load_todo_tasks

from ._common import get_repo, mcp
from ._model import TaskInfo, TaskPreview


def _list_todo_previews(repo: TaskRepo) -> list[TaskPreview]:
    return [TaskPreview.from_task(task) for task in load_todo_tasks(repo)]


def _list_root_previews(repo: TaskRepo) -> list[TaskPreview]:
    r: list[TaskPreview] = []
    for task_path in repo.list_root_tasks():
        task = parse_task_file(task_path).task
        r.append(TaskPreview.from_task(task))
    return r


def _load_task_info(repo: TaskRepo, ref: str) -> TaskInfo:
    task = resolve_ref(repo, ref).task
    return TaskInfo.from_task(task)


@mcp.tool()
def list_tasks(todo: bool = False) -> list[TaskPreview]:
    """List all root tasks (id, title, status).

    Args:
        todo: If True, list only tasks from the TODO list.
    """
    repo = get_repo()
    if todo:
        return _list_todo_previews(repo)
    return _list_root_previews(repo)


@mcp.tool()
def view_tasks(task_refs: list[str]) -> list[TaskInfo]:
    """View tasks by IDs: title, status, description, and subtask IDs.

    Use this instead of reading task files from disk.
    """
    repo = get_repo()
    return [_load_task_info(repo, ref) for ref in task_refs]


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
