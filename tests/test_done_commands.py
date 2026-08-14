"""Tests for status transition commands: done (multi-ref, JSON, --reviewed)."""

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


def test_done_shows_open_root_tasks_when_story_closes() -> None:
    s1 = create_task("Story one").task_id
    leaf = add_subtask(s1, "Only task").task_id
    s2 = create_task("Story two").task_id
    add_subtask(s2, "Remaining work")
    result = assert_invoke(app, ["done", leaf])
    # Story one is fully closed; should show other open stories
    assert "Story two" in result.output


def test_done_no_fallback_when_mixed_stories() -> None:
    s1 = create_task("Story one").task_id
    leaf1 = add_subtask(s1, "Only task").task_id
    s2 = create_task("Story two").task_id
    leaf2 = add_subtask(s2, "Task A").task_id
    add_subtask(s2, "Task B")
    s3 = create_task("Story three").task_id
    add_subtask(s3, "Unrelated")
    result = assert_invoke(app, ["done", leaf1, leaf2])
    # Story one closed entirely, but Story two still has open ancestor
    # Should NOT show Story three (the fallback listing)
    assert "Story three" not in result.output
    # But should show Story two (non-closed ancestor)
    assert "Story two" in result.output


def test_done_walks_up_past_closed_parent_to_grandparent(story_id: str) -> None:
    sub = add_subtask(story_id, "Sub-story").task_id
    leaf = add_subtask(sub, "Only leaf").task_id
    add_subtask(story_id, "Other task")
    result = assert_invoke(app, ["done", leaf])
    # Should show grandparent "My story" since parent "Sub-story" auto-closed
    assert "My story" in result.output
    assert "Other task" in result.output


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


# ---------------------------------------------------------------------------
# done --reviewed / --rev (bulk close in-review tasks)
# ---------------------------------------------------------------------------


def test_done_reviewed_closes_in_review_task(
    story_id: str, get_task_file: GetTaskFile
) -> None:
    task_id = add_subtask(story_id, "Leaf task").task_id
    assert_invoke(app, ["review", task_id])
    assert_invoke(app, ["done", "--reviewed"])
    task_file = get_task_file(story_id)
    result = parse_task_file(task_file)
    assert result.subtasks[0].status == TaskStatus.DONE


def test_done_reviewed_leaves_non_in_review_tasks_untouched(
    story_id: str, get_task_file: GetTaskFile
) -> None:
    in_review = add_subtask(story_id, "Reviewed task").task_id
    pending = add_subtask(story_id, "Pending task").task_id
    in_progress = add_subtask(story_id, "In-progress task").task_id
    assert_invoke(app, ["review", in_review])
    assert_invoke(app, ["start", in_progress])
    assert_invoke(app, ["done", "--reviewed"])
    task_file = get_task_file(story_id)
    result = parse_task_file(task_file)
    by_id = {s.id: s for s in result.subtasks}
    assert by_id[in_review].status == TaskStatus.DONE
    assert by_id[pending].status == TaskStatus.PENDING
    assert by_id[in_progress].status == TaskStatus.IN_PROGRESS


def test_done_reviewed_unions_with_explicit_refs(
    story_id: str, get_task_file: GetTaskFile
) -> None:
    in_review = add_subtask(story_id, "Reviewed task").task_id
    explicit = add_subtask(story_id, "Explicit task").task_id
    add_subtask(story_id, "Untouched task")
    assert_invoke(app, ["review", in_review])
    assert_invoke(app, ["done", "--reviewed", explicit])
    task_file = get_task_file(story_id)
    result = parse_task_file(task_file)
    by_id = {s.id: s for s in result.subtasks}
    assert by_id[in_review].status == TaskStatus.DONE
    assert by_id[explicit].status == TaskStatus.DONE


def test_done_reviewed_empty_queue_prints_info(story_id: str) -> None:
    add_subtask(story_id, "Pending task")
    result = assert_invoke(app, ["done", "--reviewed"])
    assert "No tasks to close" in result.output


def test_done_empty_lists_open_leaf_tasks(story_id: str) -> None:
    t01 = add_subtask(story_id, "Pending task").task_id
    t02 = add_subtask(story_id, "Started task").task_id
    assert_invoke(app, ["start", t02])
    result = assert_invoke(app, ["done"])
    assert "No tasks to close" in result.output
    assert t01 in result.output
    assert t02 in result.output
    assert "Pending task" in result.output
    assert "Started task" in result.output


def test_done_empty_without_open_tasks_skips_open_section(story_id: str) -> None:
    add_subtask(story_id, "Some task")
    assert_invoke(app, ["done", "--force", story_id])
    result = assert_invoke(app, ["done"])
    assert "No tasks to close" in result.output
    assert "Open tasks" not in result.output


def test_done_empty_skips_closed_tasks(story_id: str) -> None:
    t01 = add_subtask(story_id, "Done task").task_id
    t02 = add_subtask(story_id, "Pending task").task_id
    assert_invoke(app, ["done", t01])
    result = assert_invoke(app, ["done"])
    assert t01 not in result.output
    assert t02 in result.output


def test_done_empty_skips_nonleaf_tasks(story_id: str) -> None:
    sub = add_subtask(story_id, "Leaf task").task_id
    result = assert_invoke(app, ["done"])
    assert sub in result.output
    assert "My story" not in result.output


def test_done_reviewed_with_ref_when_queue_empty_closes_ref(
    story_id: str, get_task_file: GetTaskFile
) -> None:
    task_id = add_subtask(story_id, "Pending task").task_id
    assert_invoke(app, ["done", "--reviewed", task_id])
    task_file = get_task_file(story_id)
    result = parse_task_file(task_file)
    assert result.subtasks[0].status == TaskStatus.DONE


def test_done_reviewed_skips_archived_roots(
    tasks_root: Path, tasks_archive_root: Path
) -> None:
    archived_id = create_task("Archived story").task_id
    archived_sub = add_subtask(archived_id, "Archived task").task_id
    assert_invoke(app, ["review", archived_sub])
    archived_file = next(tasks_root.glob(f"{archived_id}-*.md"))
    archived_file.rename(tasks_archive_root / archived_file.name)

    live_id = create_task("Live story").task_id
    live_task = add_subtask(live_id, "Live task").task_id
    assert_invoke(app, ["review", live_task])

    assert_invoke(app, ["done", "--reviewed"])

    live_file = next(tasks_root.glob(f"{live_id}-*.md"))
    live_parsed = parse_task_file(live_file)
    assert live_parsed.subtasks[0].status == TaskStatus.DONE

    moved_file = tasks_archive_root / archived_file.name
    archived_parsed = parse_task_file(moved_file)
    assert archived_parsed.subtasks[0].status == TaskStatus.IN_REVIEW


def test_done_rev_alias_closes_in_review_task(
    story_id: str, get_task_file: GetTaskFile
) -> None:
    task_id = add_subtask(story_id, "Leaf task").task_id
    assert_invoke(app, ["review", task_id])
    assert_invoke(app, ["done", "--rev"])
    task_file = get_task_file(story_id)
    result = parse_task_file(task_file)
    assert result.subtasks[0].status == TaskStatus.DONE


def test_done_reviewed_spans_multiple_roots(tasks_root: Path) -> None:
    s1_id = create_task("Story one").task_id
    s2_id = create_task("Story two").task_id
    t1 = add_subtask(s1_id, "Task one").task_id
    t2 = add_subtask(s2_id, "Task two").task_id
    assert_invoke(app, ["review", t1])
    assert_invoke(app, ["review", t2])

    assert_invoke(app, ["done", "--reviewed"])

    s1_file = next(tasks_root.glob(f"{s1_id}-*.md"))
    s2_file = next(tasks_root.glob(f"{s2_id}-*.md"))
    assert parse_task_file(s1_file).subtasks[0].status == TaskStatus.DONE
    assert parse_task_file(s2_file).subtasks[0].status == TaskStatus.DONE
