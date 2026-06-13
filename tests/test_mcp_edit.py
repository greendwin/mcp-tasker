import pytest

from tasker.base_types import TaskStatus
from tasker.exceptions import TaskValidateError
from tasker.mcp import MutationResult, edit_task, view_tasks
from tasker.parse import parse_task_file

from .helpers import GetTaskFile, add_subtask, create_task


@pytest.fixture()
def story_id() -> str:
    return create_task("My story").task_id


def test_edit_task_returns_mutation_result(story_id: str) -> None:
    result = edit_task(story_id, title="Updated title")
    assert isinstance(result, MutationResult)


def test_edit_title(story_id: str) -> None:
    result = edit_task(story_id, title="New title")
    assert result.id == story_id
    markdown = view_tasks([story_id])
    assert "New title" in markdown


def test_edit_title_persists(story_id: str) -> None:
    edit_task(story_id, title="New title")
    markdown = view_tasks([story_id])
    assert f"# {story_id}: New title" in markdown


def test_edit_description(story_id: str) -> None:
    result = edit_task(story_id, description="A description")
    assert result.id == story_id
    markdown = view_tasks([story_id])
    assert "A description" in markdown


def test_edit_description_persists(story_id: str) -> None:
    edit_task(story_id, description="A description")
    markdown = view_tasks([story_id])
    assert "A description" in markdown


def test_edit_slug_persists(story_id: str) -> None:
    edit_task(story_id, slug="new-slug")
    markdown = view_tasks([story_id])
    assert f"# {story_id}: " in markdown


def test_edit_replaces_multi_section_body(
    story_id: str, get_task_file: GetTaskFile
) -> None:
    task_file = get_task_file(story_id)
    content = task_file.read_text()
    task_file.write_text(
        content + "\nLead paragraph.\n\n## Notes\n\nImportant note here.\n"
    )
    seeded = parse_task_file(task_file).task.description
    assert seeded is not None and "## Notes" in seeded

    edit_task(story_id, description="Replacement body")

    markdown = view_tasks([story_id])
    assert "Replacement body" in markdown
    assert "## Notes" not in markdown

    rendered = task_file.read_text()
    assert "## Notes" not in rendered
    assert "Important note here." not in rendered


def test_edit_subtask(story_id: str) -> None:
    sub_ref = add_subtask(story_id, "Sub", "Details").task_ref
    result = edit_task(sub_ref, title="Updated sub")
    markdown = view_tasks([result.id])
    assert "Updated sub" in markdown


def test_edit_not_found_raises() -> None:
    with pytest.raises(TaskValidateError):
        edit_task("s99", title="Nope")


def test_edit_no_changes(story_id: str) -> None:
    result = edit_task(story_id)
    assert result.id == story_id
    assert result.status == TaskStatus.PENDING
    markdown = view_tasks([story_id])
    assert "My story" in markdown


def test_edit_returns_status_unchanged(story_id: str) -> None:
    result = edit_task(story_id, title="New title")
    assert result.status == TaskStatus.PENDING
