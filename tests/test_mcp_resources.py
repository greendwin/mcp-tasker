from tasker.base_types import TaskStatus
from tasker.mcp import TaskInfo, TaskPreview, resource_task, resource_task_index

from .helpers import add_subtask, create_task


def test_index_empty() -> None:
    result = resource_task_index()
    assert result == []


def test_index_lists_root_tasks() -> None:
    task_id = create_task("My story").task_id
    result = resource_task_index()
    assert len(result) == 1
    assert result[0].id == task_id
    assert result[0].title == "My story"
    assert result[0].status == TaskStatus.PENDING


def test_index_returns_task_previews() -> None:
    create_task("My story")
    result = resource_task_index()
    assert isinstance(result[0], TaskPreview)


def test_index_multiple_tasks() -> None:
    create_task("First")
    create_task("Second")
    result = resource_task_index()
    assert len(result) == 2


def test_task_resource_returns_task_info() -> None:
    task_ref = create_task("My story").task_ref
    result = resource_task(task_ref)
    assert isinstance(result, TaskInfo)
    assert result.title == "My story"
    assert result.status == TaskStatus.PENDING
    assert result.description is None
    assert result.subtasks == {}


def test_task_resource_includes_subtasks() -> None:
    task_id = create_task("My story").task_id
    sub_id = add_subtask(task_id, "First subtask").task_id
    result = resource_task(task_id)
    assert result.subtasks == {"pending": [sub_id]}


def test_task_resource_subtasks_are_ids() -> None:
    task_id = create_task("My story").task_id
    add_subtask(task_id, "First subtask")
    result = resource_task(task_id)
    assert isinstance(result.subtasks["pending"][0], str)


def test_task_resource_subtask_accessible_as_resource() -> None:
    """Subtask IDs from parent can be used to access nested resources."""
    task_id = create_task("My story").task_id
    add_subtask(task_id, "First subtask")
    parent = resource_task(task_id)
    sub_id = parent.subtasks["pending"][0]
    child = resource_task(sub_id)
    assert child.title == "First subtask"


def test_task_resource_includes_description() -> None:
    task_id = create_task("My story").task_id
    sub_ref = add_subtask(task_id, "Sub", "Some details").task_ref
    result = resource_task(sub_ref)
    assert result.description == "Some details"
