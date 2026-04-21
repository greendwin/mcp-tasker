from pathlib import Path
from typing import Any

from tasker.base_types import Task, TaskStatus


class TaskerError(Exception):
    def __init__(
        self,
        message: str,
        *,
        json_output: dict[str, Any],
        file_path: Path | None = None,
    ) -> None:
        super().__init__(message)
        self.json_output = json_output
        self.file_path = file_path


class TaskValidateError(TaskerError):
    def __init__(
        self, message: str, *, task_ref: str, file_path: Path | None = None
    ) -> None:
        super().__init__(
            message, json_output={"task_ref": task_ref}, file_path=file_path
        )
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
