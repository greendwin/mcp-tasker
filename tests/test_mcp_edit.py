import pytest

from tasker.exceptions import TaskValidateError
from tasker.mcp import TaskInfo, edit_task, view_tasks

from .helpers import add_subtask, create_task


@pytest.fixture()
def story_id() -> str:
    return create_task("My story").task_id


def test_edit_task_returns_task_info(story_id: str) -> None:
    result = edit_task(story_id, title="Updated title")
    assert isinstance(result, TaskInfo)


def test_edit_title(story_id: str) -> None:
    result = edit_task(story_id, title="New title")
    assert result.title == "New title"


def test_edit_title_persists(story_id: str) -> None:
    edit_task(story_id, title="New title")
    info = view_tasks([story_id])[0]
    assert info.title == "New title"


def test_edit_description(story_id: str) -> None:
    result = edit_task(story_id, description="A description")
    assert result.description == "A description"


def test_edit_description_persists(story_id: str) -> None:
    edit_task(story_id, description="A description")
    info = view_tasks([story_id])[0]
    assert info.description == "A description"


def test_edit_slug_persists(story_id: str) -> None:
    edit_task(story_id, slug="new-slug")
    info = view_tasks([story_id])[0]
    assert info.id == story_id


def test_edit_subtask(story_id: str) -> None:
    sub_ref = add_subtask(story_id, "Sub", "Details").task_ref
    result = edit_task(sub_ref, title="Updated sub")
    assert result.title == "Updated sub"


def test_edit_not_found_raises() -> None:
    with pytest.raises(TaskValidateError):
        edit_task("s99", title="Nope")


def test_edit_no_changes(story_id: str) -> None:
    result = edit_task(story_id)
    assert result.title == "My story"
