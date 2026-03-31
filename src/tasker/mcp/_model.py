from pydantic import BaseModel
from typing_extensions import Self

from tasker.base_types import Task, TaskStatus, is_root_task_id
from tasker.parse import parse_task_ref


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
    parent_id: str | None
    description: str | None
    subtasks: list[TaskPreview] | None

    @classmethod
    def from_task(cls, task: Task) -> Self:
        if is_root_task_id(task.id):
            parent_id = None
        else:
            parent_id = parse_task_ref(task.ref).parent_id

        return cls(
            id=task.id,
            parent_id=parent_id,
            title=task.title,
            status=task.status,
            description=task.description,
            subtasks=[TaskPreview.from_task(child) for child in task.subtasks],
        )
