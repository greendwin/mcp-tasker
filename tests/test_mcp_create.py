from tasker.base_types import TaskStatus
from tasker.mcp import create_task, list_tasks, view_tasks

from .helpers import create_task as helper_create_task


def test_create_root_task_returns_task_info() -> None:
    result = create_task("My story")
    assert result.title == "My story"
    assert result.status == TaskStatus.PENDING
    assert result.parent_id is None


def test_create_root_task_appears_in_list() -> None:
    result = create_task("My story")
    output = list_tasks()
    assert result.id in output


def test_create_root_task_capitalizes_title() -> None:
    result = create_task("my story")
    assert result.title == "My story"


def test_create_root_task_with_description() -> None:
    result = create_task("My story", description="Some details")
    full = view_tasks([result.id])[0]
    assert full.description == "Some details"


def test_create_subtask_under_parent() -> None:
    parent_id = helper_create_task("Parent").task_id
    result = create_task("Child task", parent=parent_id)
    assert result.parent_id == parent_id


def test_create_subtask_appears_in_parent_subtasks() -> None:
    parent_id = helper_create_task("Parent").task_id
    child = create_task("Child task", parent=parent_id)
    parent = view_tasks([parent_id])[0]
    all_ids = [tid for ids in parent.subtasks.values() for tid in ids]
    assert child.id in all_ids


def test_create_subtask_with_description() -> None:
    parent_id = helper_create_task("Parent").task_id
    result = create_task("Child task", parent=parent_id, description="Details here")
    full = view_tasks([result.id])[0]
    assert full.description == "Details here"
