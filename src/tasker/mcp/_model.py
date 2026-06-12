from collections import defaultdict

from pydantic import BaseModel
from typing_extensions import Self

from tasker.base_types import Task, TaskStatus, is_root_task_id
from tasker.parse import parse_task_ref


class TaskIdentity(BaseModel):
    id: str
    title: str
    status: TaskStatus


class TaskPreview(TaskIdentity):
    has_body: bool = False

    @classmethod
    def from_task(cls, task: Task) -> Self:
        return cls(
            id=task.id,
            title=task.title,
            status=task.status,
            has_body=bool(task.description),
        )


class TaskInfo(TaskIdentity):
    parent_id: str | None
    description: str | None
    subtasks: dict[TaskStatus, list[str]]

    @classmethod
    def from_task(cls, task: Task) -> Self:
        if is_root_task_id(task.id):
            parent_id = None
        else:
            parent_id = parse_task_ref(task.ref).parent_id

        grouped: dict[TaskStatus, list[str]] = defaultdict(list)
        for child in task.subtasks:
            grouped[child.status].append(child.id)

        return cls(
            id=task.id,
            parent_id=parent_id,
            title=task.title,
            status=task.status,
            description=task.description,
            subtasks=grouped,
        )
