from ._common import get_repo, mcp
from ._model import TaskInfo, TaskPreview


@mcp.resource("task://index", mime_type="application/json")
def resource_task_index() -> list[TaskPreview]:
    """List all root tasks."""
    repo = get_repo()
    root_ids = repo.list_root_tasks()
    return [TaskPreview.from_task(repo.resolve_ref(rid)) for rid in root_ids]


@mcp.resource("task://{ref}", mime_type="application/json")
def resource_task(ref: str) -> TaskInfo:
    """View a task and its subtasks by reference."""
    repo = get_repo()
    task = repo.resolve_ref(ref)
    return TaskInfo.from_task(task)
