from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from tasker.base_types import Task, TaskStatus, is_root_task_id
from tasker.parse import make_child_ref, parse_task_ref
from tasker.render import append_task_filename

if TYPE_CHECKING:
    from ._task_loader import TaskLoader


def generate_slug(title: str) -> str:
    words = re.sub(r"[^a-z0-9\s]", "", title.lower()).split()[:5]
    return "-".join(words)


def find_next_root_task_id(loader: TaskLoader) -> str:
    existing = _scan_root_task_nums(loader.root) + _scan_root_task_nums(
        loader.get_tasks_root(archived=True)
    )
    return f"s{max(existing, default=0) + 1:02d}"


_RE_STORY_PREFIX = re.compile(r"^s(\d+)")


def _scan_root_task_nums(root_dir: Path) -> list[int]:
    if not root_dir.is_dir():
        return []

    return [
        int(m.group(1))
        for p in root_dir.iterdir()
        if (m := _RE_STORY_PREFIX.match(p.name))
    ]


def list_root_tasks(root: Path) -> list[Path]:
    return sorted(p for p in root.iterdir() if _RE_STORY_PREFIX.match(p.name))


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

    cur_id = task.id
    while not is_root_task_id(cur_id):
        ri = parse_task_ref(cur_id)
        parent = loader.resolve_ref(ri.parent_id)

        assert not parent.is_inline, "parent should not be inline due to subtasks"
        update_task_status_and_flags(parent, allow_downgrade=allow_downgrade)

        cur_id = parent.id


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

    if task.description or task.extra_sections:
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

    cur_id = task.id
    while not is_root_task_id(cur_id):
        ref = parse_task_ref(cur_id)
        parent = loader.resolve_ref(ref.parent_id)
        assert parent.extended, "parent must be directory-based"

        stack.append(parent)
        cur_id = parent.id

    root_task = stack[-1]
    parent_dir = loader.get_tasks_root(archived=root_task.archived)

    while stack:
        parent_dir = parent_dir / stack.pop().ref

    return append_task_filename(parent_dir, task.ref, task.extended)
