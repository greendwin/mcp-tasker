from tasker.parse import parse_task_file

from ._common import get_repo, mcp
from ._model import TaskInfo, TaskPreview


@mcp.resource("task://index", mime_type="application/json")
def resource_task_index() -> list[TaskPreview]:
    """List all root tasks."""
    repo = get_repo()

    r: list[TaskPreview] = []
    for task_path in repo.list_root_tasks():
        task = parse_task_file(task_path).task
        r.append(TaskPreview.from_task(task))

    return r


@mcp.resource("task://{ref}", mime_type="application/json")
def resource_task(ref: str) -> TaskInfo:
    """View a task and its subtasks by reference."""
    repo = get_repo()
    task = repo.resolve_ref(ref)
    return TaskInfo.from_task(task)
