import pytest

from tasker.base_types import TaskStatus
from tasker.exceptions import TaskValidateError
from tasker.mcp import TaskInfo, TaskPreview, list_tasks, view_tasks

from .helpers import add_subtask, create_task


def test_list_tasks_returns_empty() -> None:
    result = list_tasks()
    assert result == []


def test_list_tasks_returns_task() -> None:
    task_id = create_task("My story").task_id
    result = list_tasks()
    assert len(result) == 1
    assert result[0].id == task_id
    assert result[0].title == "My story"
    assert result[0].status == TaskStatus.PENDING


def test_list_tasks_returns_task_preview_instances() -> None:
    create_task("My story")
    result = list_tasks()
    assert type(result[0]) is TaskPreview


def test_list_tasks_multiple_root_tasks() -> None:
    create_task("First story")
    create_task("Second story")
    result = list_tasks()
    assert len(result) == 2
    titles = {t.title for t in result}
    assert titles == {"First story", "Second story"}


def test_view_tasks_returns_task_info() -> None:
    task_id = create_task("My story").task_id
    result = view_tasks([task_id])[0]
    assert isinstance(result, TaskInfo)
    assert result.id == task_id
    assert result.title == "My story"
    assert result.status == TaskStatus.PENDING
    assert result.subtasks == []


def test_view_tasks_includes_description() -> None:
    task_id = create_task("My story").task_id
    sub_ref = add_subtask(task_id, "Sub", "Some details").task_ref
    result = view_tasks([sub_ref])[0]
    assert result.description == "Some details"


def test_view_tasks_no_description_is_none() -> None:
    task_id = create_task("My story").task_id
    result = view_tasks([task_id])[0]
    assert result.description is None


def test_view_tasks_subtasks_are_ids() -> None:
    task_id = create_task("My story").task_id
    sub_id = add_subtask(task_id, "Sub").task_id
    result = view_tasks([task_id])[0]
    assert result.subtasks == [sub_id]


def test_view_tasks_subtasks_no_title() -> None:
    task_id = create_task("My story").task_id
    add_subtask(task_id, "Sub")
    result = view_tasks([task_id])[0]
    # subtasks are plain strings (IDs), not objects with a title attribute
    assert isinstance(result.subtasks[0], str)


def test_view_tasks_not_found_raises() -> None:
    with pytest.raises(TaskValidateError):
        view_tasks(["s99"])


def test_view_tasks_returns_multiple() -> None:
    id1 = create_task("First").task_id
    id2 = create_task("Second").task_id
    results = view_tasks([id1, id2])
    assert len(results) == 2
    ids = {r.id for r in results}
    assert ids == {id1, id2}


def test_view_tasks_empty_list() -> None:
    assert view_tasks([]) == []


def test_view_tasks_returns_task_info_instances() -> None:
    task_id = create_task("Story").task_id
    results = view_tasks([task_id])
    assert isinstance(results[0], TaskInfo)
