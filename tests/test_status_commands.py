"""Tests for status transition commands: start, review, reset, cancel, done."""

import json
from pathlib import Path
from typing import Any

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


def test_start_shows_extra_sections(get_task_file: GetTaskFile) -> None:
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


# ---------------------------------------------------------------------------
# reset
# ---------------------------------------------------------------------------


def test_reset_in_progress_leaf_task_succeeds(story_id: str) -> None:
    task_id = add_subtask(story_id, "Leaf task").task_id
    assert_invoke(app, ["start", task_id])
    result = assert_invoke(app, ["reset", task_id])
    assert task_id in result.output


def test_reset_leaf_task_updates_status_on_disk(
    story_id: str, get_task_file: GetTaskFile
) -> None:
    task_id = add_subtask(story_id, "Leaf task").task_id
    assert_invoke(app, ["start", task_id])
    assert_invoke(app, ["reset", task_id])
    task_file = get_task_file(story_id)
    content = task_file.read_text()
    assert f"- [ ] {task_id}: Leaf task" in content


def test_reset_leaf_task_parses_as_pending(
    story_id: str, get_task_file: GetTaskFile
) -> None:
    task_id = add_subtask(story_id, "Leaf task").task_id
    assert_invoke(app, ["start", task_id])
    assert_invoke(app, ["reset", task_id])
    task_file = get_task_file(story_id)
    result = parse_task_file(task_file)
    assert result.subtasks[0].status == TaskStatus.PENDING


def test_reset_already_pending_succeeds(story_id: str) -> None:
    task_id = add_subtask(story_id, "Leaf task").task_id
    result = assert_invoke(app, ["reset", task_id])
    assert "already pending" in result.output


def test_reset_done_task(story_id: str, get_task_file: GetTaskFile) -> None:
    task_id = add_subtask(story_id, "Leaf task").task_id
    assert_invoke(app, ["done", task_id])
    assert_invoke(app, ["reset", task_id])
    task_file = get_task_file(story_id)
    result = parse_task_file(task_file)
    assert result.subtasks[0].status == TaskStatus.PENDING


def test_reset_cancelled_task(story_id: str, get_task_file: GetTaskFile) -> None:
    task_id = add_subtask(story_id, "Leaf task").task_id
    assert_invoke(app, ["cancel", task_id])
    assert_invoke(app, ["reset", task_id])
    task_file = get_task_file(story_id)
    result = parse_task_file(task_file)
    assert result.subtasks[0].status == TaskStatus.PENDING


def test_reset_cancelled_task_removes_strikethrough(
    story_id: str, get_task_file: GetTaskFile
) -> None:
    task_id = add_subtask(story_id, "Leaf task").task_id
    assert_invoke(app, ["cancel", task_id])
    assert_invoke(app, ["reset", task_id])
    task_file = get_task_file(story_id)
    content = task_file.read_text()
    assert f"- [ ] {task_id}: Leaf task" in content
    assert "~~" not in content


def test_reset_subtask_updates_parent_status(
    story_id: str, get_task_file: GetTaskFile
) -> None:
    t01 = add_subtask(story_id, "Task one").task_id
    t02 = add_subtask(story_id, "Task two").task_id
    assert_invoke(app, ["start", t01])
    assert_invoke(app, ["start", t02])
    # reset both — parent should go back to pending
    assert_invoke(app, ["reset", t01])
    assert_invoke(app, ["reset", t02])
    task_file = get_task_file(story_id)
    task = parse_task_file(task_file).task
    assert task.status == TaskStatus.PENDING


def test_reset_one_subtask_parent_stays_in_progress(
    story_id: str,
    get_task_file: GetTaskFile,
) -> None:
    t01 = add_subtask(story_id, "Task one").task_id
    t02 = add_subtask(story_id, "Task two").task_id
    assert_invoke(app, ["start", t01])
    assert_invoke(app, ["start", t02])
    assert_invoke(app, ["reset", t01])
    task_file = get_task_file(story_id)
    task = parse_task_file(task_file).task
    assert task.status == TaskStatus.IN_PROGRESS


def test_reset_pending_nonleaf_succeeds(story_id: str) -> None:
    add_subtask(story_id, "Subtask one")
    add_subtask(story_id, "Subtask two")
    result = assert_invoke(app, ["reset", story_id])
    assert "already pending" in result.output


def test_reset_in_progress_nonleaf_fails(story_id: str) -> None:
    task_id = add_subtask(story_id, "Subtask one").task_id
    assert_invoke(app, ["start", task_id])
    result = assert_invoke(app, ["reset", story_id], expect_error=True)
    assert "has subtasks" in result.output
    assert "managed automatically" in result.output


def test_reset_nonleaf_hints_force(story_id: str) -> None:
    task_id = add_subtask(story_id, "Subtask one").task_id
    assert_invoke(app, ["start", task_id])
    result = assert_invoke(app, ["reset", story_id], expect_error=True)
    assert "--force" in result.output


def test_reset_done_nonleaf_lists_non_pending_subtasks(story_id: str) -> None:
    t01 = add_subtask(story_id, "Subtask one").task_id
    t02 = add_subtask(story_id, "Subtask two").task_id
    assert_invoke(app, ["done", t01])
    assert_invoke(app, ["done", t02])
    result = assert_invoke(app, ["reset", story_id], expect_error=True)
    assert "--force" in result.output
    assert t01 in result.output
    assert t02 in result.output


def test_reset_force_succeeds_with_non_pending_subtasks(story_id: str) -> None:
    add_subtask(story_id, "Subtask one")
    add_subtask(story_id, "Subtask two")
    assert_invoke(app, ["start", f"{story_id}t01"])
    assert_invoke(app, ["done", f"{story_id}t02"])
    assert_invoke(app, ["reset", "--force", story_id])


def test_reset_force_marks_all_subtasks_pending(
    story_id: str, get_task_file: GetTaskFile
) -> None:
    add_subtask(story_id, "Subtask one")
    add_subtask(story_id, "Subtask two")
    assert_invoke(app, ["start", f"{story_id}t01"])
    assert_invoke(app, ["done", f"{story_id}t02"])
    assert_invoke(app, ["reset", "--force", story_id])
    task_file = get_task_file(story_id)
    result = parse_task_file(task_file)
    assert all(t.status == TaskStatus.PENDING for t in result.subtasks)


def test_reset_force_marks_parent_pending(
    story_id: str, get_task_file: GetTaskFile
) -> None:
    add_subtask(story_id, "Subtask one")
    add_subtask(story_id, "Subtask two")
    assert_invoke(app, ["done", f"{story_id}t01"])
    assert_invoke(app, ["done", f"{story_id}t02"])
    assert_invoke(app, ["reset", "--force", story_id])
    task_file = get_task_file(story_id)
    task = parse_task_file(task_file).task
    assert task.status == TaskStatus.PENDING


def test_reset_force_prints_forcibly_reset_subtasks(story_id: str) -> None:
    t01 = add_subtask(story_id, "Subtask one").task_id
    t02 = add_subtask(story_id, "Subtask two").task_id
    assert_invoke(app, ["start", t01])
    assert_invoke(app, ["done", t02])
    result = assert_invoke(app, ["reset", "--force", story_id])
    assert t01 in result.output
    assert t02 in result.output


def test_reset_force_on_leaf_task_works(
    story_id: str, get_task_file: GetTaskFile
) -> None:
    task_id = add_subtask(story_id, "Leaf task").task_id
    assert_invoke(app, ["start", task_id])
    assert_invoke(app, ["reset", "--force", task_id])
    task_file = get_task_file(story_id)
    result = parse_task_file(task_file)
    assert result.subtasks[0].status == TaskStatus.PENDING


def test_reset_force_json_includes_forced_task_ids(story_id: str) -> None:
    t01 = add_subtask(story_id, "Subtask one").task_id
    t02 = add_subtask(story_id, "Subtask two").task_id
    assert_invoke(app, ["start", t01])
    assert_invoke(app, ["done", t02])
    result = assert_invoke(app, ["--json-output", "reset", "--force", story_id])
    data = json.loads(result.output)
    assert set(data["forced_task_ids"]) == {t01, t02}


def test_reset_force_json_empty_when_nothing_forced(story_id: str) -> None:
    add_subtask(story_id, "Subtask one")
    add_subtask(story_id, "Subtask two")
    result = assert_invoke(app, ["--json-output", "reset", "--force", story_id])
    data = json.loads(result.output)
    assert "forced_task_ids" not in data


def test_reset_nonexistent_task_fails() -> None:
    assert_invoke(app, ["reset", "s99t01"], expect_error=True)


def test_json_reset_outputs_task_ref(story_id: str) -> None:
    task_id = add_subtask(story_id, "Leaf task").task_id
    assert_invoke(app, ["start", task_id])
    result = assert_invoke(app, ["--json-output", "reset", task_id])
    data = json.loads(result.output)
    assert data["task_refs"] == [task_id]


def test_json_reset_nonexistent_outputs_error() -> None:
    result = assert_invoke(app, ["--json-output", "reset", "s99t01"], expect_error=True)
    data = json.loads(result.output)
    assert "error" in data


def test_json_reset_already_pending(story_id: str) -> None:
    task_id = add_subtask(story_id, "Leaf task").task_id
    result = assert_invoke(app, ["--json-output", "reset", task_id])
    data = json.loads(result.output)
    assert data["task_refs"] == [task_id]


def test_reset_idempotent_flushes_corrected_statuses(
    story_id: str, get_task_file: GetTaskFile
) -> None:
    """Manual edit: mark subtask pending, but parent still in-progress on disk.

    Running `reset` on the subtask is idempotent (already pending), but
    the corrected parent status must still be flushed to disk.
    """
    task_id = add_subtask(story_id, "Task one").task_id
    task_file = get_task_file(story_id)

    # simulate manual edit: mark subtask in-progress but leave parent pending
    content = task_file.read_text()
    patched = content.replace("- [ ]", "- [~]").replace(
        "status: pending", "status: in-progress"
    )
    task_file.write_text(patched)

    # now reset the subtask — it was in-progress, should go to pending
    assert_invoke(app, ["reset", task_id])

    # parent status must now be corrected on disk
    updated = task_file.read_text()
    assert "status: pending" in updated


def test_reset_filebased_leaf_with_description_stays_filebased(
    story_id: str, tasks_root: Path
) -> None:
    """File-based task with description stays file-based after reset."""
    task_id = add_subtask(story_id, "My task", details="Keep me").task_id
    assert_invoke(app, ["start", task_id])
    assert_invoke(app, ["reset", task_id])

    # Task file should still exist
    story_dir = next(tasks_root.glob(f"{story_id}-*/"))
    task_files = list(story_dir.glob(f"{task_id}-*.md"))
    assert len(task_files) == 1


def test_reset_shows_task_title(story_id: str) -> None:
    task_id = add_subtask(story_id, "My leaf task").task_id
    assert_invoke(app, ["start", task_id])
    result = assert_invoke(app, ["reset", task_id])
    assert "My leaf task" in result.output


def test_reset_shows_parent_preview(story_id: str) -> None:
    task_id = add_subtask(story_id, "My leaf task", "Some details here").task_id
    assert_invoke(app, ["start", task_id])
    result = assert_invoke(app, ["reset", task_id])
    assert "My story" in result.output
    assert "My leaf task" in result.output


def test_reset_no_description_no_extra_output(story_id: str) -> None:
    task_id = add_subtask(story_id, "My leaf task").task_id
    assert_invoke(app, ["start", task_id])
    result = assert_invoke(app, ["reset", task_id])
    assert "None" not in result.output


# ---------------------------------------------------------------------------
# cancel
# ---------------------------------------------------------------------------


def test_cancel_pending_leaf_task_succeeds(story_id: str) -> None:
    task_id = add_subtask(story_id, "Leaf task").task_id
    result = assert_invoke(app, ["cancel", task_id])
    assert task_id in result.output


def test_cancel_leaf_task_updates_status_on_disk(
    story_id: str, get_task_file: GetTaskFile
) -> None:
    task_id = add_subtask(story_id, "Leaf task").task_id
    assert_invoke(app, ["cancel", task_id])
    task_file = get_task_file(story_id)
    content = task_file.read_text()
    assert f"- [x] ~~{task_id}: Leaf task~~" in content


def test_cancel_leaf_task_parses_as_cancelled(
    story_id: str, get_task_file: GetTaskFile
) -> None:
    task_id = add_subtask(story_id, "Leaf task").task_id
    assert_invoke(app, ["cancel", task_id])
    task_file = get_task_file(story_id)
    result = parse_task_file(task_file)
    assert result.subtasks[0].status == TaskStatus.CANCELLED


def test_cancel_preserves_title_without_strikethrough(
    story_id: str, get_task_file: GetTaskFile
) -> None:
    task_id = add_subtask(story_id, "Leaf task").task_id
    assert_invoke(app, ["cancel", task_id])
    task_file = get_task_file(story_id)
    result = parse_task_file(task_file)
    assert result.subtasks[0].title == "Leaf task"


def test_cancel_already_cancelled_succeeds(story_id: str) -> None:
    task_id = add_subtask(story_id, "Leaf task").task_id
    assert_invoke(app, ["cancel", task_id])
    result = assert_invoke(app, ["cancel", task_id])
    assert "already cancelled" in result.output


def test_cancel_in_progress_task(story_id: str, get_task_file: GetTaskFile) -> None:
    task_id = add_subtask(story_id, "Leaf task").task_id
    assert_invoke(app, ["start", task_id])
    assert_invoke(app, ["cancel", task_id])
    task_file = get_task_file(story_id)
    result = parse_task_file(task_file)
    assert result.subtasks[0].status == TaskStatus.CANCELLED


def test_cancel_done_task(story_id: str, get_task_file: GetTaskFile) -> None:
    task_id = add_subtask(story_id, "Leaf task").task_id
    assert_invoke(app, ["done", task_id])
    result = assert_invoke(app, ["cancel", task_id])
    assert "cancelled" in result.output
    task_file = get_task_file(story_id)
    parsed = parse_task_file(task_file)
    assert parsed.subtasks[0].status == TaskStatus.CANCELLED


def test_cancel_subtask_sets_parent_cancelled_when_only_subtask(
    story_id: str,
    get_task_file: GetTaskFile,
) -> None:
    task_id = add_subtask(story_id, "Leaf task").task_id
    assert_invoke(app, ["cancel", task_id])
    task_file = get_task_file(story_id)
    task = parse_task_file(task_file).task
    assert task.status == TaskStatus.CANCELLED


def test_cancel_all_subtasks_sets_parent_cancelled(
    story_id: str, get_task_file: GetTaskFile
) -> None:
    t01 = add_subtask(story_id, "Task one").task_id
    t02 = add_subtask(story_id, "Task two").task_id
    assert_invoke(app, ["cancel", t01])
    assert_invoke(app, ["cancel", t02])
    task_file = get_task_file(story_id)
    task = parse_task_file(task_file).task
    assert task.status == TaskStatus.CANCELLED


def test_mixed_done_and_cancelled_sets_parent_done(
    story_id: str, get_task_file: GetTaskFile
) -> None:
    t01 = add_subtask(story_id, "Task one").task_id
    t02 = add_subtask(story_id, "Task two").task_id
    assert_invoke(app, ["done", t01])
    assert_invoke(app, ["cancel", t02])
    task_file = get_task_file(story_id)
    task = parse_task_file(task_file).task
    assert task.status == TaskStatus.DONE


def test_cancel_subtask_parent_stays_pending_when_sibling_pending(
    story_id: str,
    get_task_file: GetTaskFile,
) -> None:
    task_id = add_subtask(story_id, "Task one").task_id
    add_subtask(story_id, "Task two")
    assert_invoke(app, ["cancel", task_id])
    task_file = get_task_file(story_id)
    task = parse_task_file(task_file).task
    assert task.status == TaskStatus.PENDING


def test_cancel_task_with_subtasks_fails(story_id: str) -> None:
    add_subtask(story_id, "Subtask one")
    add_subtask(story_id, "Subtask two")
    result = assert_invoke(app, ["cancel", story_id], expect_error=True)
    assert "has subtasks" in result.output
    assert "managed automatically" in result.output


def test_cancel_nonleaf_hints_force(story_id: str) -> None:
    add_subtask(story_id, "Subtask one")
    result = assert_invoke(app, ["cancel", story_id], expect_error=True)
    assert "--force" in result.output


def test_cancel_force_succeeds_with_open_subtasks(story_id: str) -> None:
    add_subtask(story_id, "Subtask one")
    add_subtask(story_id, "Subtask two")
    assert_invoke(app, ["cancel", "--force", story_id])


def test_cancel_force_marks_all_subtasks_cancelled(
    story_id: str, get_task_file: GetTaskFile
) -> None:
    add_subtask(story_id, "Subtask one")
    add_subtask(story_id, "Subtask two")
    assert_invoke(app, ["cancel", "--force", story_id])
    task_file = get_task_file(story_id)
    result = parse_task_file(task_file)
    assert all(t.status == TaskStatus.CANCELLED for t in result.subtasks)


def test_cancel_force_marks_parent_cancelled(
    story_id: str, get_task_file: GetTaskFile
) -> None:
    add_subtask(story_id, "Subtask one")
    add_subtask(story_id, "Subtask two")
    assert_invoke(app, ["cancel", "--force", story_id])
    task_file = get_task_file(story_id)
    task = parse_task_file(task_file).task
    assert task.status == TaskStatus.CANCELLED


def test_cancel_force_prints_forcibly_cancelled_subtasks(
    story_id: str,
) -> None:
    t01 = add_subtask(story_id, "Subtask one").task_id
    t02 = add_subtask(story_id, "Subtask two").task_id
    result = assert_invoke(app, ["cancel", "--force", story_id])
    assert t01 in result.output
    assert t02 in result.output


def test_cancel_force_does_not_list_already_cancelled_subtasks(
    story_id: str,
) -> None:
    t01 = add_subtask(story_id, "Subtask one").task_id
    t02 = add_subtask(story_id, "Subtask two").task_id
    assert_invoke(app, ["cancel", t01])
    result = assert_invoke(app, ["cancel", "--force", story_id])
    assert t01 not in result.output
    assert t02 in result.output


def test_cancel_force_preserves_done_subtasks(
    story_id: str, get_task_file: GetTaskFile
) -> None:
    t01 = add_subtask(story_id, "Subtask one").task_id
    add_subtask(story_id, "Subtask two")
    assert_invoke(app, ["done", t01])
    assert_invoke(app, ["cancel", "--force", story_id])
    task_file = get_task_file(story_id)
    result = parse_task_file(task_file)
    assert result.subtasks[0].status == TaskStatus.DONE
    assert result.subtasks[1].status == TaskStatus.CANCELLED


def test_cancel_nonexistent_task_fails() -> None:
    assert_invoke(app, ["cancel", "s99t01"], expect_error=True)


def test_cancel_force_on_leaf_task_works(
    story_id: str, get_task_file: GetTaskFile
) -> None:
    task_id = add_subtask(story_id, "Leaf task").task_id
    assert_invoke(app, ["cancel", "--force", task_id])
    task_file = get_task_file(story_id)
    result = parse_task_file(task_file)
    assert result.subtasks[0].status == TaskStatus.CANCELLED


def test_done_force_skips_cancelled_subtasks(story_id: str) -> None:
    t01 = add_subtask(story_id, "Subtask one").task_id
    t02 = add_subtask(story_id, "Subtask two").task_id
    assert_invoke(app, ["cancel", t01])
    result = assert_invoke(app, ["done", "--force", story_id])
    assert t01 not in result.output
    assert t02 in result.output


def test_json_cancel_outputs_task_ref(story_id: str) -> None:
    task_id = add_subtask(story_id, "Leaf task").task_id
    result = assert_invoke(app, ["--json-output", "cancel", task_id])
    data = json.loads(result.output)
    assert data["task_refs"] == [task_id]


def test_json_cancel_force_includes_forced_task_ids(
    story_id: str,
) -> None:
    t01 = add_subtask(story_id, "Subtask one").task_id
    t02 = add_subtask(story_id, "Subtask two").task_id
    result = assert_invoke(app, ["--json-output", "cancel", "--force", story_id])
    data = json.loads(result.output)
    assert set(data["forced_task_ids"]) == {t01, t02}


def test_json_cancel_nonexistent_outputs_error() -> None:
    result = assert_invoke(
        app, ["--json-output", "cancel", "s99t01"], expect_error=True
    )
    data = json.loads(result.output)
    assert "error" in data


def test_cancel_already_cancelled_nonleaf_succeeds(story_id: str) -> None:
    add_subtask(story_id, "Subtask one")
    assert_invoke(app, ["cancel", "--force", story_id])
    result = assert_invoke(app, ["cancel", story_id])
    assert "already cancelled" in result.output


def test_cancel_already_cancelled_nonleaf_json_succeeds(
    story_id: str,
) -> None:
    add_subtask(story_id, "Subtask one")
    assert_invoke(app, ["cancel", "--force", story_id])
    result = assert_invoke(app, ["--json-output", "cancel", story_id])
    data = json.loads(result.output)
    assert data["task_refs"] == [f"{story_id}-my-story"]


def test_cancel_shows_parent_task(story_id: str) -> None:
    task_id = add_subtask(story_id, "My leaf task").task_id
    result = assert_invoke(app, ["cancel", task_id])
    assert "My story" in result.output


def test_cancel_shows_sibling_tasks(story_id: str) -> None:
    task_id = add_subtask(story_id, "First task").task_id
    add_subtask(story_id, "Second task")
    result = assert_invoke(app, ["cancel", task_id])
    assert "First task" in result.output
    assert "Second task" in result.output


def test_cancel_root_task_no_parent_shown(story_id: str) -> None:
    task_id = add_subtask(story_id, "Only subtask").task_id
    assert_invoke(app, ["cancel", task_id])
    assert_invoke(app, ["cancel", story_id, "--force"])  # root — no parent shown


def test_cancel_json_does_not_show_parent(story_id: str) -> None:
    task_id = add_subtask(story_id, "My leaf task").task_id
    result = assert_invoke(app, ["--json-output", "cancel", task_id])
    data = json.loads(result.output)
    assert data["task_refs"] == [task_id]
    assert "parent" not in data


def test_cancel_idempotent_flushes_corrected_statuses(
    story_id: str, get_task_file: GetTaskFile
) -> None:
    """Manual edit: mark subtask cancelled, but parent still pending on disk.

    Running `cancel` on the subtask is idempotent (already cancelled), but
    the corrected parent status must still be flushed to disk.
    """
    task_id = add_subtask(story_id, "Task one").task_id
    task_file = get_task_file(story_id)

    # simulate manual edit: mark subtask cancelled but leave parent pending
    content = task_file.read_text()
    patched = content.replace(
        "- [ ] " + f"{task_id}: Task one",
        "- [x] ~~" + f"{task_id}: Task one~~",
    )
    assert "status: pending" in patched
    task_file.write_text(patched)

    # idempotent cancel on already-cancelled subtask
    result = assert_invoke(app, ["cancel", task_id])
    assert "already cancelled" in result.output

    # parent status must now be corrected on disk
    updated = task_file.read_text()
    assert "status: cancelled" in updated


# ---------------------------------------------------------------------------
# done
# ---------------------------------------------------------------------------


def test_stop_pending_leaf_task_succeeds(story_id: str) -> None:
    task_id = add_subtask(story_id, "Leaf task").task_id
    result = assert_invoke(app, ["done", task_id])
    assert task_id in result.output


def test_stop_leaf_task_updates_status_on_disk(
    story_id: str, get_task_file: GetTaskFile
) -> None:
    task_id = add_subtask(story_id, "Leaf task").task_id
    assert_invoke(app, ["done", task_id])
    task_file = get_task_file(story_id)
    content = task_file.read_text()
    assert f"- [x] {task_id}: Leaf task" in content


def test_stop_leaf_task_parses_as_done(
    story_id: str, get_task_file: GetTaskFile
) -> None:
    task_id = add_subtask(story_id, "Leaf task").task_id
    assert_invoke(app, ["done", task_id])
    task_file = get_task_file(story_id)
    result = parse_task_file(task_file)
    assert result.subtasks[0].status == TaskStatus.DONE


def test_stop_already_done_task_succeeds(story_id: str) -> None:
    task_id = add_subtask(story_id, "Leaf task").task_id
    assert_invoke(app, ["done", task_id])
    result = assert_invoke(app, ["done", task_id])
    assert "already finished" in result.output


def test_stop_in_progress_task_marks_done(
    story_id: str, get_task_file: GetTaskFile
) -> None:
    task_id = add_subtask(story_id, "Leaf task").task_id
    assert_invoke(app, ["start", task_id])
    assert_invoke(app, ["done", task_id])
    task_file = get_task_file(story_id)
    result = parse_task_file(task_file)
    assert result.subtasks[0].status == TaskStatus.DONE


def test_stop_subtask_sets_parent_done_when_only_subtask(
    story_id: str, get_task_file: GetTaskFile
) -> None:
    task_id = add_subtask(story_id, "Leaf task").task_id
    assert_invoke(app, ["done", task_id])
    task_file = get_task_file(story_id)
    task = parse_task_file(task_file).task
    assert task.status == TaskStatus.DONE


def test_stop_subtask_parent_stays_in_progress_when_sibling_pending(
    story_id: str,
    get_task_file: GetTaskFile,
) -> None:
    t01 = add_subtask(story_id, "Task one").task_id
    add_subtask(story_id, "Task two")
    assert_invoke(app, ["done", t01])
    task_file = get_task_file(story_id)
    task = parse_task_file(task_file).task
    assert task.status == TaskStatus.PENDING


def test_stop_task_with_subtasks_fails(story_id: str) -> None:
    add_subtask(story_id, "Subtask one")
    add_subtask(story_id, "Subtask two")
    result = assert_invoke(app, ["done", story_id], expect_error=True)
    assert "has subtasks" in result.output
    assert "managed automatically" in result.output


def test_stop_task_with_subtasks_lists_pending(story_id: str) -> None:
    t01 = add_subtask(story_id, "Subtask one").task_id
    t02 = add_subtask(story_id, "Subtask two").task_id
    result = assert_invoke(app, ["done", story_id], expect_error=True)
    assert t01 in result.output
    assert t02 in result.output


def test_stop_nonexistent_task_fails() -> None:
    assert_invoke(app, ["done", "s99t01"], expect_error=True)


def test_done_nonleaf_hints_force(story_id: str) -> None:
    add_subtask(story_id, "Subtask one")
    result = assert_invoke(app, ["done", story_id], expect_error=True)
    assert "--force" in result.output


def test_done_force_succeeds_with_open_subtasks(story_id: str) -> None:
    add_subtask(story_id, "Subtask one")
    add_subtask(story_id, "Subtask two")
    assert_invoke(app, ["done", "--force", story_id])


def test_done_force_marks_all_subtasks_done(
    story_id: str, get_task_file: GetTaskFile
) -> None:
    add_subtask(story_id, "Subtask one")
    add_subtask(story_id, "Subtask two")
    assert_invoke(app, ["done", "--force", story_id])
    task_file = get_task_file(story_id)
    result = parse_task_file(task_file)
    assert all(t.status == TaskStatus.DONE for t in result.subtasks)


def test_done_force_marks_parent_done(
    story_id: str, get_task_file: GetTaskFile
) -> None:
    add_subtask(story_id, "Subtask one")
    add_subtask(story_id, "Subtask two")
    assert_invoke(app, ["done", "--force", story_id])
    task_file = get_task_file(story_id)
    task = parse_task_file(task_file).task
    assert task.status == TaskStatus.DONE


def test_done_force_on_leaf_task_works(
    story_id: str, get_task_file: GetTaskFile
) -> None:
    task_id = add_subtask(story_id, "Leaf task").task_id
    assert_invoke(app, ["done", "--force", task_id])
    task_file = get_task_file(story_id)
    result = parse_task_file(task_file)
    assert result.subtasks[0].status == TaskStatus.DONE


def test_done_force_prints_forcibly_closed_subtasks(story_id: str) -> None:
    t01 = add_subtask(story_id, "Subtask one").task_id
    t02 = add_subtask(story_id, "Subtask two").task_id
    result = assert_invoke(app, ["done", "--force", story_id])
    assert t01 in result.output
    assert t02 in result.output


def test_done_force_does_not_list_already_done_subtasks(story_id: str) -> None:
    t01 = add_subtask(story_id, "Subtask one").task_id
    t02 = add_subtask(story_id, "Subtask two").task_id
    assert_invoke(app, ["done", t01])
    result = assert_invoke(app, ["done", "--force", story_id])
    assert t01 not in result.output
    assert t02 in result.output


def test_done_force_no_output_when_all_already_done(story_id: str) -> None:
    task_id = add_subtask(story_id, "Subtask one").task_id
    assert_invoke(app, ["done", task_id])
    result = assert_invoke(app, ["done", "--force", story_id])
    assert "Forcibly" not in result.output


def test_done_force_json_includes_forced_task_ids(story_id: str) -> None:
    t01 = add_subtask(story_id, "Subtask one").task_id
    t02 = add_subtask(story_id, "Subtask two").task_id
    result = assert_invoke(app, ["--json-output", "done", "--force", story_id])
    data = json.loads(result.output)
    assert set(data["forced_task_ids"]) == {t01, t02}


def test_done_force_json_empty_when_nothing_forced(story_id: str) -> None:
    task_id = add_subtask(story_id, "Subtask one").task_id
    assert_invoke(app, ["done", task_id])
    result = assert_invoke(app, ["--json-output", "done", "--force", story_id])
    data = json.loads(result.output)
    assert data.get("forced_task_ids") is None


def test_done_already_done_nonleaf_succeeds(story_id: str) -> None:
    add_subtask(story_id, "Subtask one")
    assert_invoke(app, ["done", "--force", story_id])
    result = assert_invoke(app, ["done", story_id])
    assert "already finished" in result.output


def test_done_already_done_nonleaf_json_succeeds(story_id: str) -> None:
    add_subtask(story_id, "Subtask one")
    assert_invoke(app, ["done", "--force", story_id])
    result = assert_invoke(app, ["--json-output", "done", story_id])
    data = json.loads(result.output)
    assert data["task_refs"] == [f"{story_id}-my-story"]


def test_done_idempotent_flushes_corrected_statuses(
    story_id: str, get_task_file: GetTaskFile
) -> None:
    """Manual edit: mark subtask done, but parent still pending on disk.

    Running `done` on the subtask is idempotent (already done), but
    the corrected parent status must still be flushed to disk.
    """
    task_id = add_subtask(story_id, "Task one").task_id
    task_file = get_task_file(story_id)

    # simulate manual edit: mark subtask done but leave parent pending
    content = task_file.read_text()
    patched = content.replace("- [ ]", "- [x]")
    assert "status: pending" in patched
    task_file.write_text(patched)

    # idempotent done on already-done subtask
    result = assert_invoke(app, ["done", task_id])
    assert "already finished" in result.output

    # parent status must now be corrected on disk
    updated = task_file.read_text()
    assert "status: done" in updated


def test_done_shows_parent_task(story_id: str) -> None:
    task_id = add_subtask(story_id, "My leaf task").task_id
    result = assert_invoke(app, ["done", task_id])
    assert "My story" in result.output


def test_done_shows_sibling_tasks(story_id: str) -> None:
    task_id = add_subtask(story_id, "First task").task_id
    add_subtask(story_id, "Second task")
    result = assert_invoke(app, ["done", task_id])
    assert "First task" in result.output
    assert "Second task" in result.output


def test_done_root_task_no_parent_shown(story_id: str) -> None:
    # Root tasks have no parent — finishing one should not crash
    task_id = add_subtask(story_id, "Only subtask").task_id
    assert_invoke(app, ["done", task_id])
    assert_invoke(app, ["done", story_id])  # root task done — no parent shown


def test_done_json_does_not_show_parent(story_id: str) -> None:
    task_id = add_subtask(story_id, "My leaf task").task_id
    result = assert_invoke(app, ["--json-output", "done", task_id])
    data = json.loads(result.output)
    assert data["task_refs"] == [task_id]
    # No parent info in JSON output
    assert "parent" not in data


# ---------------------------------------------------------------------------
# Multiple refs (from test_multi_ref.py)
# ---------------------------------------------------------------------------


def test_start_multiple_tasks(story_id: str) -> None:
    t01 = add_subtask(story_id, "Task one").task_id
    t02 = add_subtask(story_id, "Task two").task_id
    result = assert_invoke(app, ["start", t01, t02])
    assert t01 in result.output
    assert t02 in result.output


def test_start_multiple_updates_disk(story_id: str, get_task_file: GetTaskFile) -> None:
    t01 = add_subtask(story_id, "Task one").task_id
    t02 = add_subtask(story_id, "Task two").task_id
    assert_invoke(app, ["start", t01, t02])
    task_file = get_task_file(story_id)
    result = parse_task_file(task_file)
    assert result.subtasks[0].status == TaskStatus.IN_PROGRESS
    assert result.subtasks[1].status == TaskStatus.IN_PROGRESS


def test_start_multiple_with_already_started(story_id: str) -> None:
    t01 = add_subtask(story_id, "Task one").task_id
    t02 = add_subtask(story_id, "Task two").task_id
    assert_invoke(app, ["start", t01])
    result = assert_invoke(app, ["start", t01, t02])
    assert "already started" in result.output
    assert t02 in result.output


def test_done_multiple_tasks(story_id: str) -> None:
    t01 = add_subtask(story_id, "Task one").task_id
    t02 = add_subtask(story_id, "Task two").task_id
    result = assert_invoke(app, ["done", t01, t02])
    assert t01 in result.output
    assert t02 in result.output


def test_done_multiple_updates_disk(story_id: str, get_task_file: GetTaskFile) -> None:
    t01 = add_subtask(story_id, "Task one").task_id
    t02 = add_subtask(story_id, "Task two").task_id
    assert_invoke(app, ["done", t01, t02])
    task_file = get_task_file(story_id)
    result = parse_task_file(task_file)
    assert result.subtasks[0].status == TaskStatus.DONE
    assert result.subtasks[1].status == TaskStatus.DONE
    assert result.task.status == TaskStatus.DONE


def test_done_multiple_with_already_finished(story_id: str) -> None:
    t01 = add_subtask(story_id, "Task one").task_id
    t02 = add_subtask(story_id, "Task two").task_id
    assert_invoke(app, ["done", t01])
    result = assert_invoke(app, ["done", t01, t02])
    assert "already finished" in result.output
    assert t02 in result.output


def test_cancel_multiple_tasks(story_id: str) -> None:
    t01 = add_subtask(story_id, "Task one").task_id
    t02 = add_subtask(story_id, "Task two").task_id
    result = assert_invoke(app, ["cancel", t01, t02])
    assert t01 in result.output
    assert t02 in result.output


def test_cancel_multiple_updates_disk(
    story_id: str, get_task_file: GetTaskFile
) -> None:
    t01 = add_subtask(story_id, "Task one").task_id
    t02 = add_subtask(story_id, "Task two").task_id
    assert_invoke(app, ["cancel", t01, t02])
    task_file = get_task_file(story_id)
    result = parse_task_file(task_file)
    assert result.subtasks[0].status == TaskStatus.CANCELLED
    assert result.subtasks[1].status == TaskStatus.CANCELLED


def test_cancel_multiple_with_already_cancelled(story_id: str) -> None:
    t01 = add_subtask(story_id, "Task one").task_id
    t02 = add_subtask(story_id, "Task two").task_id
    assert_invoke(app, ["cancel", t01])
    result = assert_invoke(app, ["cancel", t01, t02])
    assert "already cancelled" in result.output
    assert t02 in result.output


def test_reset_multiple_tasks(story_id: str) -> None:
    t01 = add_subtask(story_id, "Task one").task_id
    t02 = add_subtask(story_id, "Task two").task_id
    assert_invoke(app, ["start", t01])
    assert_invoke(app, ["start", t02])
    result = assert_invoke(app, ["reset", t01, t02])
    assert t01 in result.output
    assert t02 in result.output


def test_reset_multiple_updates_disk(story_id: str, get_task_file: GetTaskFile) -> None:
    t01 = add_subtask(story_id, "Task one").task_id
    t02 = add_subtask(story_id, "Task two").task_id
    assert_invoke(app, ["start", t01])
    assert_invoke(app, ["start", t02])
    assert_invoke(app, ["reset", t01, t02])
    task_file = get_task_file(story_id)
    result = parse_task_file(task_file)
    assert result.subtasks[0].status == TaskStatus.PENDING
    assert result.subtasks[1].status == TaskStatus.PENDING
    assert result.task.status == TaskStatus.PENDING


def test_reset_multiple_with_already_pending(story_id: str) -> None:
    t01 = add_subtask(story_id, "Task one").task_id
    t02 = add_subtask(story_id, "Task two").task_id
    assert_invoke(app, ["start", t02])
    result = assert_invoke(app, ["reset", t01, t02])
    assert "already pending" in result.output
    assert t02 in result.output


def test_json_start_multiple(story_id: str) -> None:
    t01 = add_subtask(story_id, "Task one").task_id
    t02 = add_subtask(story_id, "Task two").task_id
    result = assert_invoke(app, ["--json-output", "start", t01, t02])
    data = json.loads(result.output)
    assert data["task_refs"] == [t01, t02]


def test_json_done_multiple(story_id: str) -> None:
    t01 = add_subtask(story_id, "Task one").task_id
    t02 = add_subtask(story_id, "Task two").task_id
    result = assert_invoke(app, ["--json-output", "done", t01, t02])
    data = json.loads(result.output)
    assert data["task_refs"] == [t01, t02]


def test_done_multiple_shows_single_parent_preview(story_id: str) -> None:
    t01 = add_subtask(story_id, "Task one").task_id
    t02 = add_subtask(story_id, "Task two").task_id
    result = assert_invoke(app, ["done", t01, t02])
    # parent "My story" should appear only once (combined preview)
    assert result.output.count("My story") == 1


def test_done_multiple_highlights_all_tasks(story_id: str) -> None:
    t01 = add_subtask(story_id, "Task one").task_id
    t02 = add_subtask(story_id, "Task two").task_id
    result = assert_invoke(app, ["done", t01, t02])
    # both tasks should be highlighted with <<<
    assert result.output.count("<<<") == 2


def test_cancel_multiple_shows_single_parent_preview(story_id: str) -> None:
    t01 = add_subtask(story_id, "Task one").task_id
    t02 = add_subtask(story_id, "Task two").task_id
    result = assert_invoke(app, ["cancel", t01, t02])
    assert result.output.count("My story") == 1


def test_cancel_multiple_highlights_all_tasks(story_id: str) -> None:
    t01 = add_subtask(story_id, "Task one").task_id
    t02 = add_subtask(story_id, "Task two").task_id
    result = assert_invoke(app, ["cancel", t01, t02])
    assert result.output.count("<<<") == 2


def test_reset_multiple_shows_single_parent_preview(story_id: str) -> None:
    t01 = add_subtask(story_id, "Task one").task_id
    t02 = add_subtask(story_id, "Task two").task_id
    assert_invoke(app, ["start", t01])
    assert_invoke(app, ["start", t02])
    result = assert_invoke(app, ["reset", t01, t02])
    assert result.output.count("My story") == 1


def test_reset_multiple_highlights_all_tasks(story_id: str) -> None:
    t01 = add_subtask(story_id, "Task one").task_id
    t02 = add_subtask(story_id, "Task two").task_id
    assert_invoke(app, ["start", t01])
    assert_invoke(app, ["start", t02])
    result = assert_invoke(app, ["reset", t01, t02])
    assert result.output.count("<<<") == 2


def test_done_cross_level_shows_single_tree(story_id: str) -> None:
    """Tasks at different depths share one preview rooted at common ancestor."""
    t01 = add_subtask(story_id, "Task one").task_id
    t02 = add_subtask(story_id, "Task two").task_id
    t0101 = add_subtask(t01, "Subtask A").task_id
    result = assert_invoke(app, ["done", t0101, t02])
    # "My story" (common ancestor) should appear only once
    assert result.output.count("My story") == 1
    # "Task one" should appear only once (as child of story, not as separate parent)
    assert result.output.count("Task one") == 1
    # both finished tasks are highlighted
    assert result.output.count("<<<") == 2


def test_cancel_cross_level_highlights_all(story_id: str) -> None:
    t01 = add_subtask(story_id, "Task one").task_id
    t0101 = add_subtask(t01, "Subtask A").task_id
    t02 = add_subtask(story_id, "Task two").task_id
    result = assert_invoke(app, ["cancel", t0101, t02])
    assert result.output.count("My story") == 1
    assert result.output.count("<<<") == 2


# ---------------------------------------------------------------------------
# JSON output for start and done (from test_json_output.py)
# ---------------------------------------------------------------------------


def _parse_json(output: str) -> Any:
    return json.loads(output.strip())


def test_json_start_outputs_task_ref() -> None:
    assert_invoke(app, ["new", "My story"])
    assert_invoke(app, ["add", "s01", "Leaf task"])
    result = assert_invoke(app, ["--json-output", "start", "s01t01"])
    data = _parse_json(result.output)
    assert data["task_refs"] == ["s01t01"]


def test_json_start_nonleaf_outputs_error() -> None:
    assert_invoke(app, ["new", "My story"])
    assert_invoke(app, ["add", "s01", "Leaf task"])
    result = assert_invoke(app, ["--json-output", "start", "s01"], expect_error=True)
    data = _parse_json(result.output)
    assert "error" in data


def test_json_start_nonexistent_outputs_error() -> None:
    result = assert_invoke(app, ["--json-output", "start", "s99t01"], expect_error=True)
    data = _parse_json(result.output)
    assert "error" in data


def test_json_done_outputs_task_ref() -> None:
    assert_invoke(app, ["new", "My story"])
    assert_invoke(app, ["add", "s01", "Leaf task"])
    result = assert_invoke(app, ["--json-output", "done", "s01t01"])
    data = _parse_json(result.output)
    assert data["task_refs"] == ["s01t01"]


def test_json_done_nonleaf_outputs_error() -> None:
    assert_invoke(app, ["new", "My story"])
    assert_invoke(app, ["add", "s01", "Leaf task"])
    result = assert_invoke(app, ["--json-output", "done", "s01"], expect_error=True)
    data = _parse_json(result.output)
    assert "error" in data


def test_json_done_force_outputs_task_ref() -> None:
    assert_invoke(app, ["new", "My story"])
    assert_invoke(app, ["add", "s01", "Subtask one"])
    assert_invoke(app, ["add", "s01", "Subtask two"])
    result = assert_invoke(app, ["--json-output", "done", "--force", "s01"])
    data = _parse_json(result.output)
    assert data["task_refs"] == ["s01-my-story"]


def test_json_done_force_includes_forced_task_ids() -> None:
    assert_invoke(app, ["new", "My story"])
    assert_invoke(app, ["add", "s01", "Subtask one"])
    assert_invoke(app, ["add", "s01", "Subtask two"])
    result = assert_invoke(app, ["--json-output", "done", "--force", "s01"])
    data = _parse_json(result.output)
    forced = data["forced_task_ids"]
    assert set(forced) == {"s01t01", "s01t02"}


def test_json_done_force_no_forced_when_all_done() -> None:
    assert_invoke(app, ["new", "My story"])
    assert_invoke(app, ["add", "s01", "Subtask one"])
    assert_invoke(app, ["done", "s01t01"])
    result = assert_invoke(app, ["--json-output", "done", "--force", "s01"])
    data = _parse_json(result.output)
    assert data.get("forced_task_ids") is None


def test_json_done_nonexistent_outputs_error() -> None:
    result = assert_invoke(app, ["--json-output", "done", "s99t01"], expect_error=True)
    data = _parse_json(result.output)
    assert "error" in data
