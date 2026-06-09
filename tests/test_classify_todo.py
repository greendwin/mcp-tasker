from tasker.base_types import Task, TaskStatus
from tasker.todo import classify_todo


def _task(task_id: str, status: TaskStatus = TaskStatus.PENDING) -> Task:
    return Task(id=task_id, title=task_id, status=status)


def test_empty_list_is_not_all_finished() -> None:
    result = classify_todo([])
    assert result.active == []
    assert result.all_finished is False


def test_all_closed_is_all_finished() -> None:
    tasks = [_task("s01", TaskStatus.DONE), _task("s02", TaskStatus.CANCELLED)]
    result = classify_todo(tasks)
    assert result.active == []
    assert result.all_finished is True


def test_keeps_only_active_tasks() -> None:
    s1, s2, s3 = _task("s01"), _task("s02", TaskStatus.DONE), _task("s03")
    result = classify_todo([s1, s2, s3])
    assert result.active == [s1, s3]
    assert result.all_finished is False
