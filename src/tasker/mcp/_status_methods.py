from tasker.base_types import TaskStatus
from tasker.resolve import save_closed_refs

from ._common import get_repo, mcp
from ._model import TaskInfo, TaskPreview


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
def start_task(task_ref: str) -> TaskPreview:
    """Mark a task as in-progress."""
    repo = get_repo()
    task = repo.resolve_ref(task_ref)
    repo.start_task(task)
    repo.flush_to_disk()
    return TaskPreview.from_task(task)


@mcp.tool()
def review_task(task_ref: str) -> TaskPreview:
    """Mark a task as in-review (submit for review)."""
    repo = get_repo()
    task = repo.resolve_ref(task_ref)
    repo.review_task(task)
    repo.flush_to_disk()
    return TaskPreview.from_task(task)


@mcp.tool()
def reset_task(task_ref: str, force: bool = False) -> TaskPreview:
    """Reset a task back to pending.

    Use force=True to reset all non-pending subtasks.
    """
    repo = get_repo()
    task = repo.resolve_ref(task_ref)
    repo.reset_task(task, force=force)
    repo.flush_to_disk()
    return TaskPreview.from_task(task)


@mcp.tool()
def cancel_task(task_ref: str, force: bool = False) -> TaskPreview:
    """Cancel a task. Use force=True to cancel all open subtasks."""
    repo = get_repo()
    task = repo.resolve_ref(task_ref)
    already_cancelled = task.status == TaskStatus.CANCELLED
    repo.cancel_task(task, force=force)
    repo.flush_to_disk()

    if not already_cancelled:
        save_closed_refs(repo, [task.id])

    return TaskPreview.from_task(task)


@mcp.tool()
def finish_task(task_ref: str, force: bool = False) -> TaskPreview:
    """Mark a task as done. Use force=True to close all open subtasks."""
    repo = get_repo()
    task = repo.resolve_ref(task_ref)
    already_done = task.is_closed
    repo.finish_task(task, force=force)
    repo.flush_to_disk()

    if not already_done:
        save_closed_refs(repo, [task.id])

    return TaskPreview.from_task(task)
