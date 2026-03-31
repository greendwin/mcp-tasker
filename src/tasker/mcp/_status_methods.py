from ._common import get_repo, mcp
from ._model import TaskInfo


@mcp.tool()
def start_task(task_ref: str) -> TaskInfo:
    """Mark a task as in-progress."""
    repo = get_repo()
    task = repo.resolve_ref(task_ref)
    repo.start_task(task)
    repo.flush_to_disk()
    return TaskInfo.from_task(task)


@mcp.tool()
def reset_task(task_ref: str) -> TaskInfo:
    """Reset a task back to pending."""
    repo = get_repo()
    task = repo.resolve_ref(task_ref)
    repo.reset_task(task)
    repo.flush_to_disk()
    return TaskInfo.from_task(task)


@mcp.tool()
def finish_task(task_ref: str) -> TaskInfo:
    """Mark a task as done."""
    repo = get_repo()
    task = repo.resolve_ref(task_ref)
    repo.finish_task(task)
    repo.flush_to_disk()
    return TaskInfo.from_task(task)
