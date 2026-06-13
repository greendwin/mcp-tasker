from tasker.base_types import TaskStatus
from tasker.mcp import MutationResult, create_task, list_tasks, view_tasks

from .helpers import create_task as helper_create_task


def test_create_root_task_returns_mutation_result() -> None:
    result = create_task("My story")
    assert isinstance(result, MutationResult)
    assert result.id
    assert result.status == TaskStatus.PENDING


def test_mutation_result_has_no_echo_fields() -> None:
    fields = MutationResult.model_fields
    assert "title" not in fields
    assert "description" not in fields
    assert "parent_id" not in fields


def test_create_root_task_title_visible_via_view() -> None:
    result = create_task("My story")
    full = view_tasks([result.id])
    assert f"# {result.id}: My story" in full


def test_create_root_task_appears_in_list() -> None:
    result = create_task("My story")
    output = list_tasks()
    assert result.id in output


def test_create_root_task_capitalizes_title() -> None:
    result = create_task("my story")
    full = view_tasks([result.id])
    assert "My story" in full


def test_create_root_task_with_description() -> None:
    result = create_task("My story", description="Some details")
    full = view_tasks([result.id])
    assert "Some details" in full


def test_create_task_does_not_echo_description() -> None:
    result = create_task("My story", description="Some details")
    assert not hasattr(result, "description")
    full = view_tasks([result.id])
    assert "Some details" in full


def test_create_subtask_under_parent() -> None:
    parent_id = helper_create_task("Parent").task_id
    result = create_task("Child task", parent=parent_id)
    parent = view_tasks([parent_id])
    subtasks_part = parent.split("## Subtasks", 1)[1]
    assert result.id in subtasks_part


def test_create_subtask_appears_in_parent_subtasks() -> None:
    parent_id = helper_create_task("Parent").task_id
    child = create_task("Child task", parent=parent_id)
    parent = view_tasks([parent_id])
    subtasks_part = parent.split("## Subtasks", 1)[1]
    assert child.id in subtasks_part


def test_create_subtask_with_description() -> None:
    parent_id = helper_create_task("Parent").task_id
    result = create_task("Child task", parent=parent_id, description="Details here")
    full = view_tasks([result.id])
    assert "Details here" in full
