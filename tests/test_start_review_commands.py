"""Tests for status transition commands: start, review."""

import json
from pathlib import Path

import pytest

from tasker.base_types import TaskStatus
from tasker.cli import app
from tasker.parse import parse_task_file

from .helpers import GetTaskFile, add_subtask, assert_invoke, create_task


@pytest.fixture()
def story_id() -> str:
    return create_task("My story").task_id


# ---------------------------------------------------------------------------
# start
# ---------------------------------------------------------------------------


def test_start_pending_leaf_task_succeeds(story_id: str) -> None:
    task_id = add_subtask(story_id, "Leaf task").task_id
    result = assert_invoke(app, ["start", task_id])
    assert task_id in result.output


def test_start_leaf_task_updates_status_on_disk(
    story_id: str, get_task_file: GetTaskFile
) -> None:
    task_id = add_subtask(story_id, "Leaf task").task_id
    assert_invoke(app, ["start", task_id])
    task_file = get_task_file(story_id)
    content = task_file.read_text()
    assert f"- [~] {task_id}: Leaf task" in content


def test_start_leaf_task_parses_as_in_progress(
    story_id: str, get_task_file: GetTaskFile
) -> None:
    task_id = add_subtask(story_id, "Leaf task").task_id
    assert_invoke(app, ["start", task_id])
    task_file = get_task_file(story_id)
    result = parse_task_file(task_file)
    assert result.subtasks[0].status == TaskStatus.IN_PROGRESS


def test_start_already_in_progress_succeeds(story_id: str) -> None:
    task_id = add_subtask(story_id, "Leaf task").task_id
    assert_invoke(app, ["start", task_id])
    assert_invoke(app, ["start", task_id])  # idempotent, no error


def test_start_already_in_progress_is_idempotent(story_id: str) -> None:
    task_id = add_subtask(story_id, "Task one").task_id
    add_subtask(story_id, "Task two")
    assert_invoke(app, ["start", task_id])
    # second start should succeed without error
    result = assert_invoke(app, ["start", task_id])
    assert "already started" in result.output


def test_restart_done_task(story_id: str, get_task_file: GetTaskFile) -> None:
    # Manually create a task file with done status by reading and checking
    # We simulate by calling start twice and checking the error
    task_id = add_subtask(story_id, "Leaf task").task_id
    # Mark in-progress first, then set done manually via file content
    task_file = get_task_file(story_id)
    content = task_file.read_text()
    task_file.write_text(content.replace("- [ ]", "- [x]"))

    result = assert_invoke(app, ["start", task_id])
    assert "restart" in result.output
    task = parse_task_file(task_file).task
    assert task.status == TaskStatus.IN_PROGRESS


def test_start_task_with_subtasks_fails(story_id: str) -> None:
    add_subtask(story_id, "Subtask one")
    add_subtask(story_id, "Subtask two")
    result = assert_invoke(app, ["start", story_id], expect_error=True)
    assert "has subtasks" in result.output
    assert "managed automatically" in result.output


def test_start_task_with_subtasks_lists_pending(story_id: str) -> None:
    t01 = add_subtask(story_id, "Subtask one").task_id
    t02 = add_subtask(story_id, "Subtask two").task_id
    result = assert_invoke(app, ["start", story_id], expect_error=True)
    assert t01 in result.output
    assert t02 in result.output


def test_start_task_with_subtasks_no_pending_shows_message(
    story_id: str, get_task_file: GetTaskFile
) -> None:
    task_id = add_subtask(story_id, "Subtask one").task_id
    # Mark the only subtask as done via file
    task_file = get_task_file(story_id)
    content = task_file.read_text()
    task_file.write_text(content.replace("- [ ]", "- [x]"))
    result = assert_invoke(app, ["start", story_id], expect_error=True)
    assert "has subtasks" in result.output
    assert task_id not in result.output  # done task not listed as pending


def test_start_task_by_slug_ref(story_id: str) -> None:
    task_id = add_subtask(story_id, "Leaf task").task_id
    result = assert_invoke(app, ["start", task_id])
    assert task_id in result.output


def test_start_nonexistent_task_fails() -> None:
    assert_invoke(app, ["start", "s99t01"], expect_error=True)


def test_start_subtask_sets_parent_in_progress(
    story_id: str, get_task_file: GetTaskFile
) -> None:
    task_id = add_subtask(story_id, "Leaf task").task_id
    assert_invoke(app, ["start", task_id])
    task_file = get_task_file(story_id)
    task = parse_task_file(task_file).task
    assert task.status == TaskStatus.IN_PROGRESS


def test_start_subtask_parent_stays_pending_when_others_all_pending(
    story_id: str,
    get_task_file: GetTaskFile,
) -> None:
    # Two subtasks; start none → parent stays pending
    add_subtask(story_id, "Task one")
    add_subtask(story_id, "Task two")
    task_file = get_task_file(story_id)
    task = parse_task_file(task_file).task
    assert task.status == TaskStatus.PENDING


def test_start_in_progress_parent_succeeds(story_id: str) -> None:
    t01 = add_subtask(story_id, "Task one").task_id
    add_subtask(story_id, "Task two")
    assert_invoke(app, ["start", t01])
    # parent is now in-progress; starting it again should not fail
    assert_invoke(app, ["start", story_id])


def test_start_in_progress_parent_shows_already_started(story_id: str) -> None:
    t01 = add_subtask(story_id, "Task one").task_id
    add_subtask(story_id, "Task two")
    assert_invoke(app, ["start", t01])
    result = assert_invoke(app, ["start", story_id])
    assert "already started" in result.output


def test_start_in_progress_parent_json_succeeds(story_id: str) -> None:
    task_id = add_subtask(story_id, "Task one").task_id
    assert_invoke(app, ["start", task_id])
    result = assert_invoke(app, ["--json-output", "start", story_id])
    data = json.loads(result.output)
    assert data["task_refs"] == [f"{story_id}-my-story"]


def test_start_idempotent_flushes_corrected_statuses(
    story_id: str, get_task_file: GetTaskFile
) -> None:
    """Manual edit: mark subtask in-progress, but parent still pending on disk.

    Running `start` on the subtask is idempotent (already in-progress), but
    the corrected parent status must still be flushed to disk.
    """
    task_id = add_subtask(story_id, "Task one").task_id
    task_file = get_task_file(story_id)

    # simulate manual edit: mark subtask in-progress but leave parent pending
    content = task_file.read_text()
    patched = content.replace("- [ ]", "- [~]")
    assert "status: pending" in patched
    task_file.write_text(patched)

    # idempotent start on already-in-progress subtask
    result = assert_invoke(app, ["start", task_id])
    assert "already started" in result.output

    # parent status must now be corrected on disk
    updated = task_file.read_text()
    assert "status: in-progress" in updated


def test_start_shows_task_title(story_id: str) -> None:
    task_id = add_subtask(story_id, "My leaf task").task_id
    result = assert_invoke(app, ["start", task_id])
    assert "My leaf task" in result.output


def test_start_shows_description_when_present(story_id: str) -> None:
    task_id = add_subtask(story_id, "My leaf task", "Some details here").task_id
    result = assert_invoke(app, ["start", task_id])
    assert "Some details here" in result.output


def test_start_no_description_no_extra_output(story_id: str) -> None:
    task_id = add_subtask(story_id, "My leaf task").task_id
    result = assert_invoke(app, ["start", task_id])
    assert "None" not in result.output


def test_start_shows_body_sections(get_task_file: GetTaskFile) -> None:
    task_id = create_task("Leaf story").task_id
    task_file = get_task_file(task_id)
    content = task_file.read_text()
    task_file.write_text(content + "\n## Notes\n\nImportant note here.\n")
    result = assert_invoke(app, ["start", task_id])
    assert "Important note here." in result.output


# ---------------------------------------------------------------------------
# review
# ---------------------------------------------------------------------------


def test_review_pending_leaf_task_succeeds(story_id: str) -> None:
    task_id = add_subtask(story_id, "Leaf task").task_id
    result = assert_invoke(app, ["review", task_id])
    assert task_id in result.output


def test_review_leaf_task_updates_status_on_disk(
    story_id: str, get_task_file: GetTaskFile
) -> None:
    task_id = add_subtask(story_id, "Leaf task").task_id
    assert_invoke(app, ["review", task_id])
    task_file = get_task_file(story_id)
    content = task_file.read_text()
    assert f"- [~] {task_id}: **review** Leaf task" in content


def test_review_leaf_task_parses_as_in_review(
    story_id: str, get_task_file: GetTaskFile
) -> None:
    task_id = add_subtask(story_id, "Leaf task").task_id
    assert_invoke(app, ["review", task_id])
    task_file = get_task_file(story_id)
    result = parse_task_file(task_file)
    assert result.subtasks[0].status == TaskStatus.IN_REVIEW


def test_review_preserves_title_without_tag(
    story_id: str, get_task_file: GetTaskFile
) -> None:
    task_id = add_subtask(story_id, "Leaf task").task_id
    assert_invoke(app, ["review", task_id])
    task_file = get_task_file(story_id)
    result = parse_task_file(task_file)
    assert result.subtasks[0].title == "Leaf task"


def test_review_already_in_review_succeeds(story_id: str) -> None:
    task_id = add_subtask(story_id, "Leaf task").task_id
    assert_invoke(app, ["review", task_id])
    result = assert_invoke(app, ["review", task_id])
    assert "already in review" in result.output


def test_review_task_with_subtasks_fails(story_id: str) -> None:
    add_subtask(story_id, "Subtask one")
    add_subtask(story_id, "Subtask two")
    result = assert_invoke(app, ["review", story_id], expect_error=True)
    assert "has subtasks" in result.output
    assert "managed automatically" in result.output


def test_review_subtask_keeps_parent_in_progress(
    story_id: str, get_task_file: GetTaskFile
) -> None:
    task_id = add_subtask(story_id, "Leaf task").task_id
    assert_invoke(app, ["start", task_id])
    assert_invoke(app, ["review", task_id])
    task_file = get_task_file(story_id)
    task = parse_task_file(task_file).task
    assert task.status == TaskStatus.IN_PROGRESS


def test_done_on_in_review_task_succeeds(story_id: str) -> None:
    task_id = add_subtask(story_id, "Leaf task").task_id
    assert_invoke(app, ["review", task_id])
    result = assert_invoke(app, ["done", task_id])
    assert "finished" in result.output


def test_done_on_in_review_clears_review_tag(
    story_id: str, get_task_file: GetTaskFile
) -> None:
    task_id = add_subtask(story_id, "Leaf task").task_id
    assert_invoke(app, ["review", task_id])
    assert_invoke(app, ["done", task_id])
    task_file = get_task_file(story_id)
    content = task_file.read_text()
    assert "**review**" not in content
    assert f"- [x] {task_id}: Leaf task" in content


def test_reset_on_in_review_task_succeeds(story_id: str) -> None:
    task_id = add_subtask(story_id, "Leaf task").task_id
    assert_invoke(app, ["review", task_id])
    result = assert_invoke(app, ["reset", task_id])
    assert "reset to pending" in result.output


def test_review_file_based_task_sets_frontmatter(tasks_root: Path) -> None:
    sid = create_task("File story").task_id
    task_id = add_subtask(sid, "Leaf task", "Some details").task_id
    assert_invoke(app, ["review", task_id])
    # file-based subtask inside extended parent
    task_file = next(tasks_root.rglob(f"{task_id}-*.md"))
    content = task_file.read_text()
    assert "status: in-review" in content


def test_review_json_output(story_id: str) -> None:
    task_id = add_subtask(story_id, "Leaf task").task_id
    result = assert_invoke(app, ["--json-output", "review", task_id])
    data = json.loads(result.output)
    assert data["task_refs"] == [task_id]


def test_review_nonexistent_task_fails() -> None:
    assert_invoke(app, ["review", "s99t01"], expect_error=True)


def test_review_link_style_subtask_parses(tasks_root: Path) -> None:
    """File-based subtask with link-style entry parses in-review correctly."""
    sid = create_task("Link story").task_id
    task_id = add_subtask(sid, "Leaf task", "Some details").task_id
    assert_invoke(app, ["review", task_id])
    # parent is extended (directory) — find its README
    parent_dir = next(tasks_root.glob(f"{sid}-*/"))
    result = parse_task_file(parent_dir)
    sub = next(s for s in result.subtasks if s.id == task_id)
    assert sub.status == TaskStatus.IN_REVIEW
    assert sub.title == "Leaf task"


def test_review_shows_task_title(story_id: str) -> None:
    task_id = add_subtask(story_id, "My leaf task").task_id
    result = assert_invoke(app, ["review", task_id])
    assert "My leaf task" in result.output


def test_force_done_closes_in_review_subtask(
    story_id: str, get_task_file: GetTaskFile
) -> None:
    t01 = add_subtask(story_id, "Task one").task_id
    t02 = add_subtask(story_id, "Task two").task_id
    assert_invoke(app, ["review", t01])
    assert_invoke(app, ["start", t02])
    assert_invoke(app, ["done", story_id, "--force"])
    task_file = get_task_file(story_id)
    task = parse_task_file(task_file).task
    assert task.status == TaskStatus.DONE
