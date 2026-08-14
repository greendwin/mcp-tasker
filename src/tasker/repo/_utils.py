from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from tasker.base_types import Task, TaskStatus, is_root_task_id
from tasker.parse import make_child_ref, normalize_slug
from tasker.render import append_task_filename

if TYPE_CHECKING:
    from ._task_loader import TaskLoader


def generate_slug(title: str) -> str:
    # return first five parts of the normalized title
    return "-".join(normalize_slug(title).split("-")[:5])


def get_next_subtask_id(parent: Task) -> str:
    child_prefix = make_child_ref(parent.id, "")
    existing_nums = [
        int(t.id[len(child_prefix) :])
        for t in parent.subtasks
        if t.id.startswith(child_prefix) and len(t.id) == len(child_prefix) + 2
    ]
    return f"{child_prefix}{max(existing_nums, default=0) + 1:02d}"


def get_status_from_subtasks(task: Task) -> TaskStatus:
    subtasks = [t for t in task.subtasks if not t.deleted]
    if not subtasks:
        # no subtasks -- keep status unchanged
        return task.status

    if all(t.is_closed for t in subtasks):
        if all(t.status == TaskStatus.CANCELLED for t in subtasks):
            return TaskStatus.CANCELLED
        return TaskStatus.DONE

    if any(not t.is_closed and t.status != TaskStatus.PENDING for t in subtasks):
        # any non-pending and non-closed task treat as in-progress
        return TaskStatus.IN_PROGRESS

    return TaskStatus.PENDING


def update_parents_status(
    task: Task,
    *,
    loader: TaskLoader,
    update_itself: bool = False,
    allow_downgrade: bool = False,
) -> None:
    if update_itself:
        update_task_status_and_flags(task, allow_downgrade=allow_downgrade)

    cur = task
    while parent := loader.get_parent(cur):
        assert not parent.is_inline, "parent should not be inline due to subtasks"
        update_task_status_and_flags(parent, allow_downgrade=allow_downgrade)
        cur = parent


def update_task_status_and_flags(task: Task, *, allow_downgrade: bool) -> None:
    task.status = get_status_from_subtasks(task)

    subtasks = [s for s in task.subtasks if not s.deleted]

    if any(not s.is_inline for s in subtasks):
        # upgrade to extended (or noop if was extended already)
        task.extended = True
        return

    if not allow_downgrade:
        return

    task.extended = False

    # check whether task can be downgraded to inline
    if task.is_inline or is_root_task_id(task.id):
        # note: root tasks must be file-based
        return

    if task.description:
        return

    if not subtasks:
        # convert to inline
        task.slug = None


def upgrade_to_filebased(task: Task, *, loader: TaskLoader) -> None:
    if not task.is_inline:
        # already file-based
        return

    task.slug = generate_slug(task.title)
    update_parents_status(task, loader=loader)


def build_task_path_from_root(task: Task, *, loader: TaskLoader) -> Path:
    assert not task.is_inline, "inline tasks does not have path"

    if is_root_task_id(task.id):
        return append_task_filename(
            loader.get_tasks_root(archived=task.archived),
            task.ref,
            task.extended,
        )

    stack: list[Task] = []

    cur = task
    while parent := loader.get_parent(cur):
        assert parent.extended, "parent must be directory-based"
        stack.append(parent)
        cur = parent

    root_task = stack[-1]
    parent_dir = loader.get_tasks_root(archived=root_task.archived)

    while stack:
        parent_dir = parent_dir / stack.pop().ref

    return append_task_filename(parent_dir, task.ref, task.extended)
