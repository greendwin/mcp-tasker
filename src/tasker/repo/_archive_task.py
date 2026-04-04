from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

from tasker.base_types import Task, is_root_task_id
from tasker.exceptions import TaskValidateError
from tasker.parse import ParsedRef, parse_task_ref

if TYPE_CHECKING:
    from ._task_repo import TaskRepo


def is_archived_task_impl(repo: TaskRepo, task_ref: str) -> bool:
    ref = parse_task_ref(task_ref)
    archive_path = next(repo.archive_root.glob(f"{ref.root_id}-*"), None)
    return archive_path is not None


def archive_root_task_impl(
    repo: TaskRepo, task: Task, *, force: bool = False
) -> list[Task] | None:
    if not is_root_task_id(task.id):
        raise TaskValidateError(
            f"Only root tasks can be archived, {task.id!r} is a subtask.",
            task_ref=task.ref,
        )

    forced: list[Task] | None = None
    if not task.is_closed:
        if not force:
            raise TaskValidateError(
                f"Task {task.id!r} is not closed. "
                "Use --force to cancel open subtasks and archive",
                task_ref=task.id,
            )
        forced = repo.cancel_task(task, force=True)

    # flush before moving so files are up-to-date
    repo.flush_to_disk()

    repo.archive_root.mkdir(exist_ok=True)

    # move task file(s) to archive
    if task.extended:
        src = repo.root / task.ref
        dst = repo.archive_root / task.ref
        shutil.move(str(src), str(dst))
    else:
        src = repo.root / f"{task.ref}.md"
        dst = repo.archive_root / f"{task.ref}.md"
        shutil.move(str(src), str(dst))

    return forced


def unarchive_root_task_impl(repo: TaskRepo, task_ref: str) -> ParsedRef:
    ti = parse_task_ref(task_ref)

    if not is_root_task_id(ti.task_id):
        raise TaskValidateError(
            f"Only root tasks can be unarchived, {ti.task_id!r} is a subtask.",
            task_ref=task_ref,
        )

    candidates = list(repo.archive_root.glob(f"{ti.root_id}-*"))
    if not candidates:
        raise TaskValidateError(
            f"Task {ti.root_id!r} not found in archive",
            task_ref=ti.root_id,
        )

    src = candidates[0]
    dst = repo.root / src.name
    shutil.move(str(src), str(dst))

    return ti
