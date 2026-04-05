from __future__ import annotations

from typing import TYPE_CHECKING

from tasker.base_types import Task, is_root_task_id
from tasker.exceptions import TaskValidateError
from tasker.parse import ParsedRef, parse_task_ref

if TYPE_CHECKING:
    from ._task_repo import TaskRepo


def archive_root_task_impl(
    repo: TaskRepo, task: Task, *, force: bool = False
) -> list[Task] | None:
    if not is_root_task_id(task.id):
        raise TaskValidateError(
            f"Only root tasks can be archived, {task.id!r} is a subtask.",
            task_ref=task.ref,
        )

    if task.archived:
        # already archived
        return None

    forced: list[Task] | None = None
    if not task.is_closed:
        if not force:
            raise TaskValidateError(
                f"Task {task.id!r} is not closed. "
                "Use --force to cancel open subtasks and archive",
                task_ref=task.id,
            )
        forced = repo.cancel_task(task, force=True)

    _set_archived(task, True)
    repo.flush_to_disk()

    return forced


def _set_archived(task: Task, archived: bool) -> None:
    task.archived = archived
    for child in task.subtasks:
        _set_archived(child, archived)


def unarchive_root_task_impl(repo: TaskRepo, task_ref: str) -> ParsedRef:
    ti = parse_task_ref(task_ref)

    if not is_root_task_id(ti.task_id):
        raise TaskValidateError(
            f"Only root tasks can be unarchived, {ti.task_id!r} is a subtask.",
            task_ref=task_ref,
        )

    task = repo.resolve_ref(ti.root_id)
    if task.archived:
        _set_archived(task, False)
        repo.flush_to_disk()

    return ti
