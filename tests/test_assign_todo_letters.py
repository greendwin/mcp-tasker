from tasker.base_types import Task, TaskStatus
from tasker.todo import assign_todo_letters


def _task(task_id: str, status: TaskStatus = TaskStatus.PENDING) -> Task:
    return Task(id=task_id, title=task_id, status=status)


def test_empty_list_returns_empty_mapping() -> None:
    assert assign_todo_letters([]) == {}


def test_three_active_tasks_get_sequential_letters() -> None:
    tasks = [_task("s01"), _task("s02"), _task("s03")]
    assert assign_todo_letters(tasks) == {"s01": "ta", "s02": "tb", "s03": "tc"}


def test_closed_tasks_are_skipped() -> None:
    tasks = [
        _task("s01"),
        _task("s02", TaskStatus.DONE),
        _task("s03"),
        _task("s04", TaskStatus.CANCELLED),
        _task("s05"),
    ]
    assert assign_todo_letters(tasks) == {"s01": "ta", "s03": "tb", "s05": "tc"}


def test_more_than_26_active_tasks_get_no_letter_after_z() -> None:
    tasks = [_task(f"s{i:03d}") for i in range(30)]
    result = assign_todo_letters(tasks)
    assert result["s000"] == "ta"
    assert result["s025"] == "tz"
    for i in range(26, 30):
        assert f"s{i:03d}" not in result


def test_letters_stable_across_calls() -> None:
    tasks = [_task("s01"), _task("s02", TaskStatus.DONE), _task("s03")]
    assert assign_todo_letters(tasks) == assign_todo_letters(tasks)
