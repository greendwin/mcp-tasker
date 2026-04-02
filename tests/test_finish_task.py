import json

import pytest

from tasker.base_types import TaskStatus
from tasker.cli import app
from tasker.parse import parse_task_file

from .helpers import add_subtask, assert_invoke, create_task, GetTaskFile


@pytest.fixture()
def story_id() -> str:
    return create_task("My story").task_id


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


# --- idempotent done on nonleaf ---


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


# --- idempotent flush on manual edit ---


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
