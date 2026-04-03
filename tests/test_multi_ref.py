"""Tests for passing multiple task refs to status commands."""

import json

import pytest

from tasker.base_types import TaskStatus
from tasker.cli import app
from tasker.parse import parse_task_file

from .helpers import GetTaskFile, add_subtask, assert_invoke, create_task


@pytest.fixture()
def story_id() -> str:
    return create_task("My story").task_id


# --- start ---


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


# --- done ---


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


# --- cancel ---


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


# --- reset ---


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


# --- JSON output with multiple refs ---


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


# --- s22t09: combined preview for multiple tasks ---


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


# --- s22t13: common ancestor for cross-level tasks ---


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
