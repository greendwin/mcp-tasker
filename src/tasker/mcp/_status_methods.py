from collections.abc import Generator
from contextlib import contextmanager

from tasker.base_types import Task, TaskStatus
from tasker.repo import TaskRepo
from tasker.resolve import resolve_ref, save_closed_refs

from ._common import MutationResult, get_repo, mcp


@mcp.tool()
def edit_task(
    task_ref: str,
    title: str | None = None,
    description: str | None = None,
    slug: str | None = None,
) -> MutationResult:
    """Update a task's title, description, or slug."""
    with _mutate_task(task_ref) as (repo, task):
        repo.edit_task(task, title=title, description=description, slug=slug)
    return MutationResult.from_task(task)


@mcp.tool()
def start_task(task_ref: str) -> MutationResult:
    """Mark a task as in-progress."""
    with _mutate_task(task_ref) as (repo, task):
        repo.start_task(task)
    return MutationResult.from_task(task)


@mcp.tool()
def review_task(task_ref: str) -> MutationResult:
    """Mark a task as in-review (submit for review)."""
    with _mutate_task(task_ref) as (repo, task):
        repo.review_task(task)
    return MutationResult.from_task(task)


@mcp.tool()
def reset_task(task_ref: str, force: bool = False) -> MutationResult:
    """Reset a task back to pending.

    Use force=True to reset all non-pending subtasks.
    """
    with _mutate_task(task_ref) as (repo, task):
        cascaded = repo.reset_task(task, force=force)
    return MutationResult.from_task(task, cascaded)


@mcp.tool()
def cancel_task(task_ref: str, force: bool = False) -> MutationResult:
    """Cancel a task. Use force=True to cancel all open subtasks."""
    with _mutate_task(task_ref) as (repo, task):
        already_cancelled = task.status == TaskStatus.CANCELLED
        cascaded = repo.cancel_task(task, force=force)
    if not already_cancelled:
        save_closed_refs(repo, [task.id])
    return MutationResult.from_task(task, cascaded)


@mcp.tool()
def finish_task(task_ref: str, force: bool = False) -> MutationResult:
    """Mark a task as done. Use force=True to close all open subtasks."""
    with _mutate_task(task_ref) as (repo, task):
        already_done = task.is_closed
        cascaded = repo.finish_task(task, force=force)
    if not already_done:
        save_closed_refs(repo, [task.id])
    return MutationResult.from_task(task, cascaded)


@contextmanager
def _mutate_task(task_ref: str) -> Generator[tuple[TaskRepo, Task], None, None]:
    repo = get_repo()
    task = resolve_ref(repo, task_ref).task
    yield repo, task
    repo.flush_to_disk()
