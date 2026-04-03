import json

import pytest

from tasker.base_types import TaskStatus
from tasker.cli import app
from tasker.parse import parse_task_file

from .helpers import GetTaskFile, add_subtask, assert_invoke, create_task


@pytest.fixture()
def story_id() -> str:
    return create_task("My story").task_id


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


# --- done --force skips cancelled subtasks ---


def test_done_force_skips_cancelled_subtasks(story_id: str) -> None:
    t01 = add_subtask(story_id, "Subtask one").task_id
    t02 = add_subtask(story_id, "Subtask two").task_id
    assert_invoke(app, ["cancel", t01])
    result = assert_invoke(app, ["done", "--force", story_id])
    assert t01 not in result.output
    assert t02 in result.output


# --- JSON output ---


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


# --- idempotent cancel on nonleaf ---


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


# --- parent preview ---


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


# --- idempotent flush on manual edit ---


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
