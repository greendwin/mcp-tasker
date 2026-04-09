from tasker.base_types import TaskStatus
from tasker.resolve import save_closed_refs

from ._common import get_repo, mcp
from ._model import TaskInfo


@mcp.tool()
def edit_task(
    task_ref: str,
    title: str | None = None,
    description: str | None = None,
    slug: str | None = None,
) -> TaskInfo:
    """Update a task's title, description, or slug."""
    repo = get_repo()
    task = repo.resolve_ref(task_ref)
    repo.edit_task(task, title=title, description=description, slug=slug)
    repo.flush_to_disk()
    return TaskInfo.from_task(task)


@mcp.tool()
def start_task(task_ref: str) -> TaskInfo:
    """Mark a task as in-progress."""
    repo = get_repo()
    task = repo.resolve_ref(task_ref)
    repo.start_task(task)
    repo.flush_to_disk()
    return TaskInfo.from_task(task)


@mcp.tool()
def review_task(task_ref: str) -> TaskInfo:
    """Mark a task as in-review (submit for review)."""
    repo = get_repo()
    task = repo.resolve_ref(task_ref)
    repo.review_task(task)
    repo.flush_to_disk()
    return TaskInfo.from_task(task)


@mcp.tool()
def reset_task(task_ref: str, force: bool = False) -> TaskInfo:
    """Reset a task back to pending.

    Use force=True to reset all non-pending subtasks.
    """
    repo = get_repo()
    task = repo.resolve_ref(task_ref)
    repo.reset_task(task, force=force)
    repo.flush_to_disk()
    return TaskInfo.from_task(task)


@mcp.tool()
def cancel_task(task_ref: str, force: bool = False) -> TaskInfo:
    """Cancel a task. Use force=True to cancel all open subtasks."""
    repo = get_repo()
    task = repo.resolve_ref(task_ref)
    already_cancelled = task.status == TaskStatus.CANCELLED
    forced = repo.cancel_task(task, force=force)
    repo.flush_to_disk()

    if not already_cancelled:
        closed_ids = [task.id]
        if forced:
            closed_ids.extend(t.id for t in forced)
        save_closed_refs(repo, closed_ids)

    return TaskInfo.from_task(task)


@mcp.tool()
def finish_task(task_ref: str, force: bool = False) -> TaskInfo:
    """Mark a task as done. Use force=True to close all open subtasks."""
    repo = get_repo()
    task = repo.resolve_ref(task_ref)
    already_done = task.is_closed
    forced = repo.finish_task(task, force=force)
    repo.flush_to_disk()

    if not already_done:
        closed_ids = [task.id]
        if forced:
            closed_ids.extend(t.id for t in forced)
        save_closed_refs(repo, closed_ids)

    return TaskInfo.from_task(task)
