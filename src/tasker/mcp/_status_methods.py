from collections.abc import Generator
from contextlib import contextmanager

from tasker.base_types import Task, TaskStatus
from tasker.repo import TaskRepo
from tasker.resolve import resolve_ref, save_closed_refs

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
    with _mutate_task(task_ref) as (repo, task):
        repo.edit_task(task, title=title, description=description, slug=slug)
    return TaskInfo.from_task(task)


@mcp.tool()
def start_task(task_ref: str) -> TaskPreview:
    """Mark a task as in-progress."""
    with _mutate_task(task_ref) as (repo, task):
        repo.start_task(task)
    return TaskPreview.from_task(task)


@mcp.tool()
def review_task(task_ref: str) -> TaskPreview:
    """Mark a task as in-review (submit for review)."""
    with _mutate_task(task_ref) as (repo, task):
        repo.review_task(task)
    return TaskPreview.from_task(task)


@mcp.tool()
def reset_task(task_ref: str, force: bool = False) -> TaskPreview:
    """Reset a task back to pending.

    Use force=True to reset all non-pending subtasks.
    """
    with _mutate_task(task_ref) as (repo, task):
        repo.reset_task(task, force=force)
    return TaskPreview.from_task(task)


@mcp.tool()
def cancel_task(task_ref: str, force: bool = False) -> TaskPreview:
    """Cancel a task. Use force=True to cancel all open subtasks."""
    with _mutate_task(task_ref) as (repo, task):
        already_cancelled = task.status == TaskStatus.CANCELLED
        repo.cancel_task(task, force=force)
    if not already_cancelled:
        save_closed_refs(repo, [task.id])
    return TaskPreview.from_task(task)


@mcp.tool()
def finish_task(task_ref: str, force: bool = False) -> TaskPreview:
    """Mark a task as done. Use force=True to close all open subtasks."""
    with _mutate_task(task_ref) as (repo, task):
        already_done = task.is_closed
        repo.finish_task(task, force=force)
    if not already_done:
        save_closed_refs(repo, [task.id])
    return TaskPreview.from_task(task)


@contextmanager
def _mutate_task(task_ref: str) -> Generator[tuple[TaskRepo, Task], None, None]:
    repo = get_repo()
    task = resolve_ref(repo, task_ref).task
    yield repo, task
    repo.flush_to_disk()
