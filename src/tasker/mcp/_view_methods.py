from ._common import get_repo, mcp
from ._model import TaskInfo, TaskPreview


@mcp.tool()
def list_tasks() -> list[TaskPreview]:
    """List all root tasks."""
    repo = get_repo()
    root_ids = repo.list_root_tasks()

    # TODO: don't load full tree, we can just parse root tasks
    return [TaskInfo.from_task(repo.resolve_ref(root_id)) for root_id in root_ids]


@mcp.tool()
def view_task(task_ref: str) -> TaskInfo:
    """View detailed task info by its ID."""
    repo = get_repo()
    task = repo.resolve_ref(task_ref)
    return TaskInfo.from_task(task)
