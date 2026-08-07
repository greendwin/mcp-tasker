from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

from tasker.base_types import Task, TaskStatus, is_root_task_id, walk_tasks
from tasker.exceptions import TaskValidateError
from tasker.parse import ParsedRef, make_child_ref, parse_task_ref

from ._task_loader import TaskLoader
from ._utils import (
    get_next_subtask_id,
    update_parents_status,
    upgrade_to_filebased,
)

if TYPE_CHECKING:
    from ._task_repo import TaskRepo


class TaskRename(NamedTuple):
    old_id: str
    new_id: str


def move_task_impl(
    task: Task,
    *,
    new_parent: Task | None,
    new_id: str | None = None,
    loader: TaskLoader,
) -> list[TaskRename]:
    if new_parent is None:
        return _convert_to_root(task, new_id=new_id, loader=loader)

    if new_parent.id == task.id:
        raise TaskValidateError(
            f"Cannot move {task.id!r} under itself.",
            task_ref=task.id,
        )

    ref = parse_task_ref(task.id)
    if new_id is None and ref.parent_id == new_parent.id:
        # already under target parent
        return []

    if _is_descendant_of(new_parent.id, ancestor_id=task.id):
        raise TaskValidateError(
            f"Cannot move {task.id!r} under its descendant {new_parent.id!r}.",
            task_ref=task.id,
        )

    # detach from prev parent
    _detach_from_parent(task, loader=loader)

    # upgrade new parent if needed
    upgrade_to_filebased(new_parent, loader=loader)

    renames: list[TaskRename] = []
    prev_id = task.id

    if new_id is not None:
        assert parse_task_ref(new_id).parent_id == new_parent.id
        task.id = new_id
    else:
        task.id = get_next_subtask_id(new_parent)

    _reregister_tree(task, prev_id, renames, loader=loader)

    _set_archived(task, new_parent.archived)

    if new_parent.id != ref.parent_id:
        # reset task order id, for new parent it irrelevant
        task.order = None

    new_parent.subtasks.append(task)

    update_parents_status(
        task,
        loader=loader,
        update_itself=True,
        allow_downgrade=True,
    )

    return renames


def delete_task_impl(task: Task, *, loader: TaskLoader) -> None:
    for t in walk_tasks(task):
        t.deleted = True

    _mark_parent_done_if_empty(task, loader=loader)

    # update parent status (deleted tasks are filtered out)
    update_parents_status(
        task,
        loader=loader,
        update_itself=False,
        allow_downgrade=True,
    )


def _set_archived(task: Task, archived: bool) -> None:
    for t in walk_tasks(task):
        t.archived = archived


def _is_descendant_of(child_id: str, *, ancestor_id: str) -> bool:
    # check whether `child_id` is a strict descendant of `ancestor_id`
    prefix = ancestor_id if "t" in ancestor_id else ancestor_id + "t"
    return child_id.startswith(prefix) and len(child_id) > len(ancestor_id)


def _convert_to_root(
    task: Task, *, new_id: str | None = None, loader: TaskLoader
) -> list[TaskRename]:
    if not is_root_task_id(task.id):
        # reset outdated order id
        task.order = None

        _detach_from_parent(task, loader=loader)
    elif new_id is None:
        # already a root task and no rename
        return []

    # regenerate new ids
    renames: list[TaskRename] = []
    prev_id = task.id

    if new_id is not None:
        assert is_root_task_id(new_id)
        task.id = new_id
    else:
        task.id = loader.find_next_root_task_id()

    _reregister_tree(task, prev_id, renames, loader=loader)

    # new root tasks are always active (not archived)
    _set_archived(task, False)

    # root tasks must be file-based
    upgrade_to_filebased(task, loader=loader)

    return renames


def _detach_from_parent(task: Task, *, loader: TaskLoader) -> None:
    parent = loader.get_parent(task)
    if parent is None:
        # already detached
        return

    # detach from parent
    assert task in parent.subtasks
    parent.subtasks.remove(task)

    # this handles case when parent become a simple task:
    # in this case lets treat this parent as a story not a regular task
    # so if this story does not have childs then it's *finished*
    _mark_parent_done_if_empty(task, loader=loader)

    # allow_downgrade=True: extended→basic collapse is only permitted during move
    update_parents_status(
        parent,
        loader=loader,
        update_itself=True,
        allow_downgrade=True,
    )


def _mark_parent_done_if_empty(task: Task, *, loader: TaskLoader) -> None:
    parent = loader.get_parent(task)
    if parent is None:
        return

    if any(not t.deleted for t in parent.subtasks):
        # task has non-delete children
        return

    parent.status = TaskStatus.DONE


def _reregister_tree(
    task: Task, prev_id: str, renames: list[TaskRename], *, loader: TaskLoader
) -> None:
    loader.reregister_task(task, prev_id=prev_id)
    renames.append(TaskRename(prev_id, task.id))

    for child in task.subtasks:
        prev_child_id = child.id
        child.id = _replace_parent_id(child.id, new_parent_id=task.id)
        _reregister_tree(child, prev_child_id, renames, loader=loader)


def _replace_parent_id(task_id: str, *, new_parent_id: str) -> str:
    # Take the task's own 2-digit suffix and append it to the new parent's
    # child prefix.
    own_suffix = task_id[-2:]
    return make_child_ref(new_parent_id, own_suffix)


# --- archive / unarchive ---


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
