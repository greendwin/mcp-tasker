from typing import Any

from tasker.base_types import Task, TaskStatus


class TaskerError(Exception):
    def __init__(self, message: str, *, json_output: dict[str, Any]) -> None:
        super().__init__(message)
        self.json_output = json_output


class TaskValidateError(TaskerError):
    def __init__(self, message: str, *, task_ref: str) -> None:
        super().__init__(message, json_output={"task_ref": task_ref})
        self.task_ref = task_ref


class TaskHasSubtasksError(TaskerError):
    def __init__(self, task: Task) -> None:
        assert not task.is_inline and len(task.subtasks) > 0

        super().__init__(
            f"Task {task.id!r} has subtasks — its status is managed automatically",
            json_output={
                "task_ref": task.id,
                "pending_subtasks": [
                    p.id for p in task.subtasks if p.status == TaskStatus.PENDING
                ],
            },
        )
        self.task = task
