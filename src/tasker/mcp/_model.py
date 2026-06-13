from collections import defaultdict

from pydantic import BaseModel
from typing_extensions import Self

from tasker.base_types import Task, TaskStatus
from tasker.parse import task_parent_id


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
        parent_id = task_parent_id(task)

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
