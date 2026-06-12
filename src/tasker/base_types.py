from __future__ import annotations

from collections.abc import Iterator
from enum import Enum

from pydantic import BaseModel

EXTENDED_TASK_FILENAME = "README.md"


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in-progress"
    IN_REVIEW = "in-review"
    DONE = "done"
    CANCELLED = "cancelled"


class Task(BaseModel):
    id: str  # unique id that can be used to reference a task
    title: str  # short summary of a task
    status: TaskStatus = TaskStatus.PENDING

    # file-task fields (None/defaults for inline tasks)
    slug: str | None = None
    extended: bool = False
    description: str | None = None
    subtasks: list[Task] = []
    deleted: bool = False
    archived: bool = False

    @property
    def is_inline(self) -> bool:
        return self.slug is None

    @property
    def is_closed(self) -> bool:
        return self.status in (TaskStatus.DONE, TaskStatus.CANCELLED)

    @property
    def ref(self) -> str:
        if self.slug is not None:
            return build_task_ref(self.id, self.slug)
        return self.id


def build_task_ref(task_id: str, slug: str) -> str:
    return f"{task_id}-{slug}"


def is_root_task_id(task_id: str) -> bool:
    assert "-" not in task_id, "task id must be provided, not task ref"
    # HACK: tasks are in form s123t4567, root tasks are always s123 without `t` suffix
    return "t" not in task_id


def is_nonleaf_task(task: Task) -> bool:
    if not task.is_inline and task.subtasks:
        return True
    return False


def walk_tasks(task: Task) -> Iterator[Task]:
    yield task
    for child in task.subtasks:
        yield from walk_tasks(child)
