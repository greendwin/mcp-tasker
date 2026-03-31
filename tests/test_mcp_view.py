import pytest

from tasker.base_types import TaskStatus
from tasker.exceptions import TaskValidateError
from tasker.mcp import TaskInfo, TaskPreview, list_tasks, view_task

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


def test_view_task_returns_task_info() -> None:
    task_id = create_task("My story").task_id
    result = view_task(task_id)
    assert isinstance(result, TaskInfo)
    assert result.id == task_id
    assert result.title == "My story"
    assert result.status == TaskStatus.PENDING
    assert result.subtasks == []


def test_view_task_includes_description() -> None:
    task_id = create_task("My story").task_id
    sub_ref = add_subtask(task_id, "Sub", "Some details").task_ref
    result = view_task(sub_ref)
    assert result.description == "Some details"


def test_view_task_no_description_is_none() -> None:
    task_id = create_task("My story").task_id
    result = view_task(task_id)
    assert result.description is None


def test_view_task_not_found_raises() -> None:
    with pytest.raises(TaskValidateError):
        view_task("s99")
