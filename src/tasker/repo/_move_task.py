from __future__ import annotations

from typing import NamedTuple

from tasker.base_types import Task, is_root_task_id
from tasker.exceptions import TaskValidateError
from tasker.parse import make_child_ref, parse_task_ref

from ._task_loader import TaskLoader
from ._utils import (
    find_next_root_task_id,
    get_next_subtask_id,
    update_parents_status,
    upgrade_to_filebased,
)


class TaskRename(NamedTuple):
    old_id: str
    new_id: str


def move_task_impl(
    task: Task, *, new_parent: Task | None, loader: TaskLoader
) -> list[TaskRename]:
    if new_parent is None:
        return _convert_to_root(task, loader=loader)

    if new_parent.id == task.id:
        raise TaskValidateError(
            f"Cannot move {task.id!r} under itself.",
            task_ref=task.id,
        )

    ref = parse_task_ref(task.id)
    if ref.parent_id == new_parent.id:
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
    task.id = get_next_subtask_id(new_parent)
    _reregister_tree(task, prev_id, renames, loader=loader)

    new_parent.subtasks.append(task)
    update_parents_status(
        task,
        loader=loader,
        update_itself=True,
        allow_downgrade=True,
    )

    return renames


def delete_task_impl(task: Task, *, loader: TaskLoader) -> None:
    _mark_deleted(task)

    # update parent status (deleted tasks are filtered out)
    update_parents_status(
        task, loader=loader, update_itself=False, allow_downgrade=True
    )


def _mark_deleted(task: Task) -> None:
    task.deleted = True
    for child in task.subtasks:
        _mark_deleted(child)


def _is_descendant_of(child_id: str, *, ancestor_id: str) -> bool:
    """True when *child_id* is a strict descendant of *ancestor_id*."""
    prefix = ancestor_id if "t" in ancestor_id else ancestor_id + "t"
    return child_id.startswith(prefix) and len(child_id) > len(ancestor_id)


def _convert_to_root(task: Task, *, loader: TaskLoader) -> list[TaskRename]:
    if is_root_task_id(task.id):
        # already a root task
        return []

    _detach_from_parent(task, loader=loader)

    # regenerate new ids
    renames: list[TaskRename] = []

    prev_id = task.id
    task.id = find_next_root_task_id(loader)
    _reregister_tree(task, prev_id, renames, loader=loader)

    # root tasks must be file-based
    upgrade_to_filebased(task, loader=loader)

    return renames


def _detach_from_parent(task: Task, *, loader: TaskLoader) -> None:
    if is_root_task_id(task.id):
        # already detached
        return

    # detach from parent
    ref = parse_task_ref(task.ref)
    parent = loader.resolve_ref(ref.parent_id)

    assert task in parent.subtasks
    parent.subtasks.remove(task)

    # allow_downgrade=True: extended→basic collapse is only permitted during move
    update_parents_status(
        parent, update_itself=True, allow_downgrade=True, loader=loader
    )


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
