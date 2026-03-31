from pydantic import BaseModel
from typing_extensions import Self

from tasker.base_types import Task, TaskStatus


class TaskPreview(BaseModel):
    id: str
    title: str
    status: TaskStatus

    @classmethod
    def from_task(cls, task: Task) -> Self:
        return cls(
            id=task.id,
            title=task.title,
            status=task.status,
        )


class TaskInfo(TaskPreview):
    description: str | None = None
    subtasks: list[TaskPreview] | None = None

    @classmethod
    def from_task(cls, task: Task) -> Self:
        return cls(
            id=task.id,
            title=task.title,
            status=task.status,
            description=task.description,
            subtasks=[TaskPreview.from_task(child) for child in task.subtasks],
        )
