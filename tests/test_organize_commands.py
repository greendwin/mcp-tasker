import json
from pathlib import Path
from unittest import mock

import pytest

from tasker.base_types import TaskStatus
from tasker.cli import app
from tasker.layout import ARCHIVE_DIR
from tasker.parse import parse_task_file
from tasker.repo import TaskRepo
from tasker.todo import load_todo_ids

from .helpers import GetTaskFile, add_subtask, assert_invoke, create_task

# ---------------------------------------------------------------------------
# archive / unarchive — Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def story_id() -> str:
    return create_task("My story").task_id


@pytest.fixture()
def repo(tasks_root: Path) -> TaskRepo:
    return TaskRepo(tasks_root)


# ---------------------------------------------------------------------------
# archive / unarchive — move fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def s1() -> str:
    return create_task("Story one").task_id


@pytest.fixture()
def s2() -> str:
    return create_task("Story two").task_id


# ---------------------------------------------------------------------------
# basic archive
# ---------------------------------------------------------------------------


def test_archive_done_task(story_id: str) -> None:
    assert_invoke(app, ["done", "--force", story_id])
    result = assert_invoke(app, ["archive", story_id])
    assert "archived" in result.output


def test_archive_cancelled_task(story_id: str) -> None:
    assert_invoke(app, ["cancel", "--force", story_id])
    result = assert_invoke(app, ["archive", story_id])
    assert "archived" in result.output


def test_archive_moves_basic_file_to_archive(
    tasks_archive_root: Path, story_id: str, get_task_file: GetTaskFile
) -> None:
    assert_invoke(app, ["done", "--force", story_id])
    task_file = get_task_file(story_id)
    filename = task_file.name
    assert_invoke(app, ["archive", story_id])
    assert not task_file.exists()
    assert (tasks_archive_root / filename).exists()


def test_archive_moves_extended_dir_to_archive(
    tasks_root: Path, tasks_archive_root: Path, story_id: str
) -> None:
    add_subtask(story_id, "Subtask", details="Some details")
    assert_invoke(app, ["done", "--force", story_id])
    story_dir = next(tasks_root.glob(f"{story_id}-*/"))
    dirname = story_dir.name
    assert_invoke(app, ["archive", story_id])
    assert not story_dir.exists()
    assert (tasks_archive_root / dirname).is_dir()
    assert (tasks_archive_root / dirname / "README.md").exists()


# ---------------------------------------------------------------------------
# task must be closed
# ---------------------------------------------------------------------------


def test_archive_pending_task_fails(story_id: str) -> None:
    result = assert_invoke(app, ["archive", story_id], expect_error=True)
    assert "not closed" in result.output


def test_archive_open_task_lists_open_subtasks(story_id: str) -> None:
    add_subtask(story_id, "Open subtask")
    add_subtask(story_id, "Another open")
    result = assert_invoke(app, ["archive", story_id], expect_error=True)
    assert "not closed" in result.output
    assert "--force" in result.output


def test_archive_in_progress_task_fails(story_id: str) -> None:
    t01 = add_subtask(story_id, "Task").task_id
    assert_invoke(app, ["start", t01])
    result = assert_invoke(app, ["archive", story_id], expect_error=True)
    assert "not closed" in result.output


def test_archive_subtask_fails(story_id: str) -> None:
    t01 = add_subtask(story_id, "Subtask").task_id
    assert_invoke(app, ["done", t01])
    result = assert_invoke(app, ["archive", t01], expect_error=True)
    assert "root" in result.output.lower()
    assert "subtask" in result.output.lower()


# ---------------------------------------------------------------------------
# --force cancels open subtasks
# ---------------------------------------------------------------------------


def test_archive_force_pending_task(story_id: str) -> None:
    add_subtask(story_id, "Subtask one")
    add_subtask(story_id, "Subtask two")
    result = assert_invoke(app, ["archive", "--force", story_id])
    assert "archived" in result.output


def test_archive_force_cancels_subtasks(story_id: str) -> None:
    t01 = add_subtask(story_id, "Subtask one").task_id
    t02 = add_subtask(story_id, "Subtask two").task_id
    result = assert_invoke(app, ["archive", "--force", story_id])
    assert t01 in result.output
    assert t02 in result.output


def test_archive_force_moves_file(
    tasks_archive_root: Path, story_id: str, get_task_file: GetTaskFile
) -> None:
    add_subtask(story_id, "Subtask")
    task_file = get_task_file(story_id)
    filename = task_file.name
    assert_invoke(app, ["archive", "--force", story_id])
    assert not task_file.exists()
    assert (tasks_archive_root / filename).exists()


def test_archive_force_preserves_done_subtasks(
    tasks_archive_root: Path, story_id: str
) -> None:
    t01 = add_subtask(story_id, "Done task").task_id
    add_subtask(story_id, "Open task")
    assert_invoke(app, ["done", t01])
    result = assert_invoke(app, ["archive", "--force", story_id])
    # only open task was forcibly cancelled
    assert t01 not in result.output

    archived_file = next((tasks_archive_root).glob(f"{story_id}-*.md"))
    parsed = parse_task_file(archived_file)
    assert parsed.subtasks[0].status == TaskStatus.DONE
    assert parsed.subtasks[1].status == TaskStatus.CANCELLED


def test_archive_force_parent_status_is_done_when_some_subtasks_done(
    tasks_archive_root: Path, story_id: str
) -> None:
    t01 = add_subtask(story_id, "Done task").task_id
    add_subtask(story_id, "Open task")
    assert_invoke(app, ["done", t01])
    assert_invoke(app, ["archive", "--force", story_id])

    archived_file = next((tasks_archive_root).glob(f"{story_id}-*.md"))
    parsed = parse_task_file(archived_file)
    # root task has one DONE and one CANCELLED subtask → status should be DONE
    assert parsed.task.status == TaskStatus.DONE


def test_archive_force_already_closed_task(story_id: str) -> None:
    assert_invoke(app, ["done", "--force", story_id])
    result = assert_invoke(app, ["archive", "--force", story_id])
    assert "archived" in result.output


# ---------------------------------------------------------------------------
# archive JSON output
# ---------------------------------------------------------------------------


def test_json_archive_outputs_task_ref(story_id: str) -> None:
    assert_invoke(app, ["done", "--force", story_id])
    result = assert_invoke(app, ["--json-output", "archive", story_id])
    data = json.loads(result.output)
    assert "task_refs" in data
    assert story_id in data["task_refs"][0]


def test_json_archive_force_includes_forced_ids(story_id: str) -> None:
    t01 = add_subtask(story_id, "Task one").task_id
    t02 = add_subtask(story_id, "Task two").task_id
    result = assert_invoke(app, ["--json-output", "archive", "--force", story_id])
    data = json.loads(result.output)
    assert set(data["forced_task_ids"]) == {t01, t02}


def test_json_archive_not_closed_outputs_error(story_id: str) -> None:
    result = assert_invoke(
        app, ["--json-output", "archive", story_id], expect_error=True
    )
    data = json.loads(result.output)
    assert "error" in data


def test_archive_multiple_tasks(story_id: str) -> None:
    story2_id = create_task("Second story").task_id
    assert_invoke(app, ["done", "--force", story_id])
    assert_invoke(app, ["done", "--force", story2_id])
    result = assert_invoke(app, ["archive", story_id, story2_id])
    assert story_id in result.output
    assert story2_id in result.output


def test_json_archive_multiple_tasks(story_id: str) -> None:
    story2_id = create_task("Second story").task_id
    assert_invoke(app, ["done", "--force", story_id])
    assert_invoke(app, ["done", "--force", story2_id])
    result = assert_invoke(app, ["--json-output", "archive", story_id, story2_id])
    data = json.loads(result.output)
    assert len(data["task_refs"]) == 2
    assert any(story_id in r for r in data["task_refs"])
    assert any(story2_id in r for r in data["task_refs"])


def test_archive_nonexistent_task_fails() -> None:
    assert_invoke(app, ["archive", "s99"], expect_error=True)


# ---------------------------------------------------------------------------
# new task ID must not collide with archived IDs
# ---------------------------------------------------------------------------


def test_new_task_skips_archived_ids(story_id: str) -> None:
    assert_invoke(app, ["done", "--force", story_id])
    assert_invoke(app, ["archive", story_id])

    # create a new task — its ID must be higher than the archived one
    new = create_task("Second story")
    assert new.task_id > story_id


# ---------------------------------------------------------------------------
# actions on archived tasks work transparently
# ---------------------------------------------------------------------------


def _archive_story(story_id: str) -> None:
    assert_invoke(app, ["done", "--force", story_id])
    assert_invoke(app, ["archive", story_id])


def test_start_archived_task_works(tasks_archive_root: Path, story_id: str) -> None:
    _archive_story(story_id)
    result = assert_invoke(app, ["start", story_id])
    assert "started" in result.output.lower()
    # task stays in archive
    assert any(tasks_archive_root.glob(f"{story_id}-*"))


def test_done_archived_task_works(tasks_archive_root: Path, story_id: str) -> None:
    _archive_story(story_id)
    result = assert_invoke(app, ["done", story_id])
    assert "finished" in result.output.lower() or "already" in result.output.lower()
    assert any(tasks_archive_root.glob(f"{story_id}-*"))


def test_cancel_archived_task_works(tasks_archive_root: Path, story_id: str) -> None:
    _archive_story(story_id)
    result = assert_invoke(app, ["cancel", story_id])
    assert "cancel" in result.output.lower()
    assert any(tasks_archive_root.glob(f"{story_id}-*"))


def test_reset_archived_task_works(tasks_archive_root: Path, story_id: str) -> None:
    _archive_story(story_id)
    result = assert_invoke(app, ["reset", story_id])
    assert "pending" in result.output.lower()
    assert any(tasks_archive_root.glob(f"{story_id}-*"))


def test_edit_archived_task_does_not_unarchive(
    tasks_archive_root: Path, story_id: str
) -> None:
    _archive_story(story_id)
    result = assert_invoke(app, ["edit", story_id, "--title", "New title"])
    assert "Unarchiving" not in result.output
    assert "New title" in result.output
    # task stays in archive
    assert any(tasks_archive_root.glob(f"{story_id}-*"))


def test_add_to_archived_task_auto_unarchives(tasks_root: Path, story_id: str) -> None:
    _archive_story(story_id)
    result = assert_invoke(app, ["add", story_id, "New subtask"])
    assert "unarchiv" in result.output.lower()
    assert f"{story_id}t01" in result.output
    # task file should be back in the main directory
    assert any(tasks_root.glob(f"{story_id}-*"))


def test_archive_already_archived_task_reports_already(story_id: str) -> None:
    _archive_story(story_id)
    result = assert_invoke(app, ["archive", story_id])
    assert "already archived" in result.output.lower()


def test_json_archive_already_archived_outputs_already(story_id: str) -> None:
    _archive_story(story_id)
    result = assert_invoke(app, ["--json-output", "archive", story_id])
    data = json.loads(result.output)
    assert "task_refs" in data
    assert data.get("already") is True


def test_json_start_archived_task_works(story_id: str) -> None:
    _archive_story(story_id)
    result = assert_invoke(app, ["--json-output", "start", story_id])
    data = json.loads(result.output)
    assert "task_refs" in data


# ---------------------------------------------------------------------------
# unarchive command
# ---------------------------------------------------------------------------


def test_unarchive_restores_basic_file(tasks_root: Path, story_id: str) -> None:
    _archive_story(story_id)
    task_file = next((tasks_root / ARCHIVE_DIR).glob(f"{story_id}-*.md"))
    filename = task_file.name
    result = assert_invoke(app, ["unarchive", story_id])
    assert "unarchived" in result.output
    assert not task_file.exists()
    assert (tasks_root / filename).exists()


def test_unarchive_restores_extended_dir(tasks_root: Path, story_id: str) -> None:
    add_subtask(story_id, "Subtask", details="Some details")
    assert_invoke(app, ["done", "--force", story_id])
    assert_invoke(app, ["archive", story_id])
    archived_dir = next((tasks_root / ARCHIVE_DIR).glob(f"{story_id}-*/"))
    dirname = archived_dir.name
    result = assert_invoke(app, ["unarchive", story_id])
    assert "unarchived" in result.output
    assert not archived_dir.exists()
    assert (tasks_root / dirname).is_dir()
    assert (tasks_root / dirname / "README.md").exists()


def test_unarchive_allows_actions_on_task(story_id: str) -> None:
    _archive_story(story_id)
    assert_invoke(app, ["unarchive", story_id])
    # should be able to reset and start the task again
    result = assert_invoke(app, ["reset", story_id])
    assert "pending" in result.output


def test_unarchive_nonexistent_task_fails() -> None:
    result = assert_invoke(app, ["unarchive", "s99"], expect_error=True)
    assert "not found" in result.output.lower()


def test_unarchive_active_task_reports_already(story_id: str) -> None:
    result = assert_invoke(app, ["unarchive", story_id])
    assert "already unarchived" in result.output.lower()


def test_json_unarchive_active_task_outputs_already(story_id: str) -> None:
    result = assert_invoke(app, ["--json-output", "unarchive", story_id])
    data = json.loads(result.output)
    assert "task_refs" in data
    assert data.get("already") is True


def test_unarchive_subtask_fails(story_id: str) -> None:
    t01 = add_subtask(story_id, "Subtask").task_id
    _archive_story(story_id)
    result = assert_invoke(app, ["unarchive", t01], expect_error=True)
    assert "root" in result.output.lower()


def test_json_unarchive_outputs_task_ref(story_id: str) -> None:
    _archive_story(story_id)
    result = assert_invoke(app, ["--json-output", "unarchive", story_id])
    data = json.loads(result.output)
    assert "task_refs" in data
    assert story_id in data["task_refs"][0]


def test_unarchive_multiple_tasks(story_id: str) -> None:
    story2_id = create_task("Second story").task_id
    _archive_story(story_id)
    _archive_story(story2_id)
    result = assert_invoke(app, ["unarchive", story_id, story2_id])
    assert story_id in result.output
    assert story2_id in result.output


def test_json_unarchive_multiple_tasks(story_id: str) -> None:
    story2_id = create_task("Second story").task_id
    _archive_story(story_id)
    _archive_story(story2_id)
    result = assert_invoke(app, ["--json-output", "unarchive", story_id, story2_id])
    data = json.loads(result.output)
    assert len(data["task_refs"]) == 2
    assert any(story_id in r for r in data["task_refs"])
    assert any(story2_id in r for r in data["task_refs"])


# ---------------------------------------------------------------------------
# unarchive shows preview
# ---------------------------------------------------------------------------


def test_unarchive_shows_task_title(story_id: str) -> None:
    _archive_story(story_id)
    result = assert_invoke(app, ["unarchive", story_id])
    # preview should display the task title
    assert "My story" in result.output


def test_unarchive_highlights_task(story_id: str) -> None:
    _archive_story(story_id)
    result = assert_invoke(app, ["unarchive", story_id])
    assert "<<<" in result.output


def test_unarchive_json_does_not_show_preview(story_id: str) -> None:
    _archive_story(story_id)
    result = assert_invoke(app, ["--json-output", "unarchive", story_id])
    data = json.loads(result.output)
    assert "task_refs" in data
    # JSON output should not contain preview text
    assert "<<<" not in result.output


# ---------------------------------------------------------------------------
# move archived task / to archived parent
# ---------------------------------------------------------------------------


def test_move_closed_archived_task_to_parent_stays_active(
    tasks_root: Path, story_id: str
) -> None:
    story2_id = create_task("Second story").task_id
    _archive_story(story_id)
    result = assert_invoke(app, ["move", story_id, "--parent", story2_id])
    # all tasks are closed — no unarchive needed
    assert "unarchiv" not in result.output.lower()
    assert "moved" in result.output.lower()
    # story was moved under story2, becoming non-archived
    assert any(tasks_root.glob(f"{story2_id}-*"))


def test_move_open_task_to_archived_parent_auto_unarchives(
    tasks_root: Path, story_id: str
) -> None:
    story2_id = create_task("Second story").task_id
    t01 = add_subtask(story_id, "Subtask").task_id
    _archive_story(story2_id)
    # t01 is pending (non-closed) → moving it should unarchive story2
    result = assert_invoke(app, ["move", t01, "--parent", story2_id])
    assert "unarchiv" in result.output.lower()
    assert "moved" in result.output.lower()
    # story2 should be back in tasks root
    assert any(tasks_root.glob(f"{story2_id}-*"))


def test_move_closed_task_to_archived_parent_stays_archived(
    tasks_archive_root: Path, story_id: str
) -> None:
    story2_id = create_task("Second story").task_id
    t01 = add_subtask(story_id, "Subtask").task_id
    assert_invoke(app, ["done", t01])
    _archive_story(story2_id)
    # t01 is closed → parent stays archived
    result = assert_invoke(app, ["move", t01, "--parent", story2_id])
    assert "unarchiv" not in result.output.lower()
    assert "moved" in result.output.lower()
    # story2 stays in archive
    assert any(tasks_archive_root.glob(f"{story2_id}-*"))


# ---------------------------------------------------------------------------
# --closed flag
# ---------------------------------------------------------------------------


def test_archive_closed_archives_all_closed_stories(story_id: str) -> None:
    story2_id = create_task("Second story").task_id
    story3_id = create_task("Third story (open)").task_id  # stays open
    assert_invoke(app, ["done", "--force", story_id])
    assert_invoke(app, ["done", "--force", story2_id])
    result = assert_invoke(app, ["archive", "--closed"])
    assert story_id in result.output
    assert story2_id in result.output
    assert story3_id not in result.output


def test_archive_closed_skips_open_stories(story_id: str) -> None:
    assert_invoke(app, ["done", "--force", story_id])
    open_id = create_task("Open story").task_id
    result = assert_invoke(app, ["archive", "--closed"])
    assert story_id in result.output
    assert open_id not in result.output


def test_archive_no_args_fails() -> None:
    result = assert_invoke(app, ["archive"], expect_error=True)
    assert "closed" in result.output.lower()


def test_archive_closed_with_explicit_ids(story_id: str) -> None:
    story2_id = create_task("Second story").task_id
    assert_invoke(app, ["done", "--force", story_id])
    # story2 stays open; pass it explicitly alongside --closed
    result = assert_invoke(app, ["archive", "--closed", story2_id, "--force"])
    # story_id was closed → archived via --closed
    assert story_id in result.output
    # story2_id was open but passed explicitly with --force
    assert story2_id in result.output


# ---------------------------------------------------------------------------
# auto-remove from .todo on archive
# ---------------------------------------------------------------------------


def test_archive_removes_story_from_todo(story_id: str, repo: TaskRepo) -> None:
    assert_invoke(app, ["todo", story_id])
    assert story_id in load_todo_ids(repo)
    assert_invoke(app, ["done", "--force", story_id])
    assert_invoke(app, ["archive", story_id])
    assert story_id not in load_todo_ids(repo)


def test_archive_removes_subtasks_from_todo(story_id: str, repo: TaskRepo) -> None:
    t01 = add_subtask(story_id, "Task one").task_id
    t02 = add_subtask(story_id, "Task two").task_id
    assert_invoke(app, ["todo", t01, t02])
    assert t01 in load_todo_ids(repo)
    assert_invoke(app, ["done", "--force", story_id])
    assert_invoke(app, ["archive", story_id])
    todo = load_todo_ids(repo)
    assert t01 not in todo
    assert t02 not in todo


# ---------------------------------------------------------------------------
# move --parent : basic cases
# ---------------------------------------------------------------------------


def test_move_inline_subtask_to_another_parent(s1: str, s2: str) -> None:
    t01 = add_subtask(s1, "Task A").task_id
    result = assert_invoke(app, ["move", t01, "--parent", s2])
    assert "moved" in result.output
    assert s2 in result.output


def test_move_file_subtask_to_another_parent(s1: str, s2: str) -> None:
    t01 = add_subtask(s1, "Task A", details="Has details").task_id
    result = assert_invoke(app, ["move", t01, "--parent", s2])
    assert "moved" in result.output


def test_move_root_task_under_another(s1: str, s2: str) -> None:
    result = assert_invoke(app, ["move", s1, "--parent", s2])
    assert "moved" in result.output
    assert s2 in result.output


def test_move_extended_subtask_to_another_parent(s1: str, s2: str) -> None:
    t01 = add_subtask(s1, "Parent task", details="Details").task_id
    add_subtask(t01, "Child", details="Nested details")
    result = assert_invoke(app, ["move", t01, "--parent", s2])
    assert "moved" in result.output


# ---------------------------------------------------------------------------
# move --root
# ---------------------------------------------------------------------------


def test_move_subtask_to_root(s1: str) -> None:
    t01 = add_subtask(s1, "Promote me").task_id
    result = assert_invoke(app, ["move", t01, "--root"])
    assert "moved" in result.output
    assert "root" in result.output


def test_move_inline_subtask_to_root_creates_file(s1: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Promote me").task_id
    assert_invoke(app, ["move", t01, "--root"])
    new_files = list(tasks_root.glob("s*-promote-me.md"))
    assert len(new_files) == 1


def test_move_file_subtask_to_root(s1: str) -> None:
    t01 = add_subtask(s1, "Promote me", details="Has content").task_id
    result = assert_invoke(app, ["move", t01, "--root"])
    assert "root" in result.output


def test_move_extended_subtask_to_root(s1: str) -> None:
    t01 = add_subtask(s1, "Container", details="Details").task_id
    add_subtask(t01, "Child A")
    add_subtask(t01, "Child B")
    result = assert_invoke(app, ["move", t01, "--root"])
    assert "root" in result.output


# ---------------------------------------------------------------------------
# ID recalculation
# ---------------------------------------------------------------------------


def test_renames_are_printed(s1: str, s2: str) -> None:
    t01 = add_subtask(s1, "Task").task_id
    result = assert_invoke(app, ["move", t01, "--parent", s2])
    # The old id and new id should both appear (renamed)
    assert t01 in result.output
    # new id is s2 + tNN
    assert f"{s2}t01" in result.output


def test_renames_deep_subtree(s1: str, s2: str) -> None:
    t01 = add_subtask(s1, "Level 1", details="D").task_id
    t0101 = add_subtask(t01, "Level 2").task_id
    result = assert_invoke(app, ["move", t01, "--parent", s2])
    assert t01 in result.output
    assert t0101 in result.output


def test_json_renames(s1: str, s2: str) -> None:
    t01 = add_subtask(s1, "Task").task_id
    result = assert_invoke(app, ["--json-output", "move", t01, "--parent", s2])
    data = json.loads(result.output)
    assert "renames" in data
    assert data["renames"][0]["old_id"] == t01
    assert "task_refs" in data


def test_json_move_to_root(s1: str) -> None:
    t01 = add_subtask(s1, "Task").task_id
    result = assert_invoke(app, ["--json-output", "move", t01, "--root"])
    data = json.loads(result.output)
    assert "renames" in data
    assert "task_refs" in data


# ---------------------------------------------------------------------------
# File cleanup
# ---------------------------------------------------------------------------


def test_old_basic_file_removed_after_move(s1: str, s2: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Task A", details="Details").task_id
    # find original file
    story_dir = next(tasks_root.glob(f"{s1}-*/"))
    old_file = next(story_dir.glob(f"{t01}-*.md"))
    assert old_file.exists()

    assert_invoke(app, ["move", t01, "--parent", s2])
    assert not old_file.exists()


def test_old_extended_dir_removed_after_move(
    s1: str, s2: str, tasks_root: Path
) -> None:
    t01 = add_subtask(s1, "Container", details="Details").task_id
    add_subtask(t01, "Child", details="Child details")
    story_dir = next(tasks_root.glob(f"{s1}-*/"))
    old_dir = next(story_dir.glob(f"{t01}-*/"))
    assert old_dir.is_dir()

    assert_invoke(app, ["move", t01, "--parent", s2])
    assert not old_dir.exists()


def test_old_extended_dir_with_user_data_not_removed(
    s1: str, s2: str, tasks_root: Path
) -> None:
    t01 = add_subtask(s1, "Container", details="Details").task_id
    add_subtask(t01, "Child", details="Child details")
    story_dir = next(tasks_root.glob(f"{s1}-*/"))
    old_dir = next(story_dir.glob(f"{t01}-*/"))

    # place a non-task file inside the extended directory
    user_file = old_dir / "notes.txt"
    user_file.write_text("user notes")

    result = assert_invoke(app, ["move", t01, "--parent", s2], expect_error=True)
    assert "non-task files" in result.output

    # user data must still be there
    assert user_file.exists()
    assert user_file.read_text() == "user notes"


def test_new_file_created_after_move(s1: str, s2: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Task A", details="Details").task_id
    assert_invoke(app, ["move", t01, "--parent", s2])
    # new file should be under s2's directory
    story_dir = next(tasks_root.glob(f"{s2}-*/"))
    new_files = list(story_dir.glob(f"{s2}t01-*.md"))
    assert len(new_files) == 1


def test_old_root_file_removed_when_moved_under_parent(
    s1: str, s2: str, get_task_file: GetTaskFile
) -> None:
    old_file = get_task_file(s1)
    assert old_file.exists()

    assert_invoke(app, ["move", s1, "--parent", s2])
    assert not old_file.exists()


def test_move_to_root_creates_root_file(s1: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Promote me", details="Content").task_id
    assert_invoke(app, ["move", t01, "--root"])
    # should be a new root task file
    new_files = list(tasks_root.glob("s*-promote-me.md"))
    assert len(new_files) == 1


# ---------------------------------------------------------------------------
# Parent subtask list updated
# ---------------------------------------------------------------------------


def test_old_parent_subtask_list_updated(
    s1: str, s2: str, get_task_file: GetTaskFile
) -> None:
    t01 = add_subtask(s1, "Mover").task_id
    add_subtask(s1, "Stayer")
    assert_invoke(app, ["move", t01, "--parent", s2])

    # old parent should only have "Stayer"
    story_file = get_task_file(s1)
    content = story_file.read_text()
    assert "Mover" not in content
    assert "Stayer" in content


def test_new_parent_subtask_list_updated(s1: str, s2: str, tasks_root: Path) -> None:
    add_subtask(s1, "Task A")
    assert_invoke(app, ["move", f"{s1}t01", "--parent", s2])

    # new parent should list the moved task (may be .md or dir/README.md)
    candidates = list(tasks_root.glob(f"{s2}-*"))
    assert len(candidates) == 1
    path = candidates[0]
    content = (path / "README.md").read_text() if path.is_dir() else path.read_text()
    assert f"{s2}t01" in content
    assert "Task A" in content


# ---------------------------------------------------------------------------
# Task content preserved after move
# ---------------------------------------------------------------------------


def test_moved_task_preserves_description(s1: str, s2: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Described task", details="Important details").task_id
    assert_invoke(app, ["move", t01, "--parent", s2])
    story_dir = next(tasks_root.glob(f"{s2}-*/"))
    new_file = next(story_dir.glob(f"{s2}t01-*.md"))
    parsed = parse_task_file(new_file)
    assert parsed.task.description == "Important details"


def test_moved_task_preserves_status(s1: str, s2: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Started task").task_id
    assert_invoke(app, ["start", t01])
    assert_invoke(app, ["move", t01, "--parent", s2])
    # parent may have been upgraded to extended (directory)
    candidates = list(tasks_root.glob(f"{s2}-*"))
    path = candidates[0]
    content = (path / "README.md").read_text() if path.is_dir() else path.read_text()
    assert "[~]" in content  # in-progress checkbox


def test_moved_task_preserves_inline_subtasks(
    s1: str, s2: str, tasks_root: Path
) -> None:
    t01 = add_subtask(s1, "Container", details="Details").task_id
    add_subtask(t01, "Child A")
    add_subtask(t01, "Child B")
    assert_invoke(app, ["move", t01, "--parent", s2])

    # s2 is now extended (directory) because it gained a file-backed subtask
    story_dir = next(tasks_root.glob(f"{s2}-*/"))
    assert story_dir.is_dir()
    # container is basic (inline subtasks only) — a .md file
    container_file = next(story_dir.glob(f"{s2}t01-*.md"))
    content = container_file.read_text()
    assert "Child A" in content
    assert "Child B" in content


def test_moved_extended_task_preserves_file_subtasks(
    s1: str, s2: str, tasks_root: Path
) -> None:
    t01 = add_subtask(s1, "Container", details="Details").task_id
    add_subtask(t01, "Child A", details="A details")
    add_subtask(t01, "Child B", details="B details")
    assert_invoke(app, ["move", t01, "--parent", s2])

    story_dir = next(tasks_root.glob(f"{s2}-*/"))
    container_dir = next(story_dir.glob(f"{s2}t01-*/"))
    assert container_dir.is_dir()
    readme = container_dir / "README.md"
    assert readme.exists()
    content = readme.read_text()
    assert "Child A" in content
    assert "Child B" in content


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------


def test_move_requires_flag(s1: str) -> None:
    t01 = add_subtask(s1, "Task").task_id
    result = assert_invoke(app, ["move", t01], expect_error=True)
    assert "--parent" in result.output or "--root" in result.output


def test_move_rejects_both_flags(s1: str, s2: str) -> None:
    t01 = add_subtask(s1, "Task").task_id
    result = assert_invoke(
        app, ["move", t01, "--parent", s2, "--root"], expect_error=True
    )
    assert "only one" in result.output.lower()


def test_move_root_to_root_is_idempotent(s1: str) -> None:
    result = assert_invoke(app, ["move", s1, "--root"])
    assert "already" in result.output.lower()


def test_move_under_self_fails(s1: str) -> None:
    result = assert_invoke(app, ["move", s1, "--parent", s1], expect_error=True)
    assert "itself" in result.output.lower()


def test_move_under_descendant_fails(s1: str) -> None:
    t01 = add_subtask(s1, "Child", details="Details").task_id
    result = assert_invoke(app, ["move", s1, "--parent", t01], expect_error=True)
    assert "descendant" in result.output.lower()


def test_move_to_same_parent_is_idempotent(s1: str) -> None:
    t01 = add_subtask(s1, "Child").task_id
    result = assert_invoke(app, ["move", t01, "--parent", s1])
    assert "already" in result.output.lower()


def test_move_nonexistent_task_fails() -> None:
    assert_invoke(app, ["move", "s99", "--root"], expect_error=True)


def test_move_nonexistent_parent_fails(s1: str) -> None:
    t01 = add_subtask(s1, "Task").task_id
    assert_invoke(app, ["move", t01, "--parent", "s99"], expect_error=True)


# ---------------------------------------------------------------------------
# JSON output for errors
# ---------------------------------------------------------------------------


def test_json_move_error(s1: str) -> None:
    result = assert_invoke(
        app, ["--json-output", "move", s1, "--parent", s1], expect_error=True
    )
    data = json.loads(result.output)
    assert "error" in data


def test_json_move_idempotent(s1: str) -> None:
    result = assert_invoke(app, ["--json-output", "move", s1, "--root"])
    data = json.loads(result.output)
    assert data.get("already") is True
    assert "task_refs" in data


# ---------------------------------------------------------------------------
# Source parent downgrade after move
# ---------------------------------------------------------------------------


def test_move_last_file_subtask_downgrades_source_to_basic(
    s1: str, s2: str, tasks_root: Path
) -> None:
    """Moving the only file-based subtask out should downgrade the source
    from extended (directory) to basic (single file)."""
    t01 = add_subtask(s1, "File task", details="Has details").task_id

    # Source is extended (directory)
    src_dirs = list(tasks_root.glob(f"{s1}-*/"))
    assert len(src_dirs) == 1
    assert src_dirs[0].is_dir()

    assert_invoke(app, ["move", t01, "--parent", s2])

    # Source should now be a basic file, not a directory
    src_files = list(tasks_root.glob(f"{s1}-*.md"))
    assert len(src_files) == 1
    assert src_files[0].is_file()

    # Old directory should be gone
    src_dirs_after = [p for p in tasks_root.glob(f"{s1}-*") if p.is_dir()]
    assert src_dirs_after == []


def test_move_one_of_two_file_subtasks_keeps_source_extended(
    s1: str, s2: str, tasks_root: Path
) -> None:
    """Moving one file subtask while another remains should keep
    the source as extended (directory)."""
    add_subtask(s1, "Task A", details="Details A")
    t02 = add_subtask(s1, "Task B", details="Details B").task_id

    assert_invoke(app, ["move", t02, "--parent", s2])

    # Source should still be extended (directory)
    src_dirs = [p for p in tasks_root.glob(f"{s1}-*") if p.is_dir()]
    assert len(src_dirs) == 1


def test_move_all_subtasks_downgrades_parent_to_inline(
    s1: str, s2: str, tasks_root: Path
) -> None:
    """Moving all subtasks from a parent without description should
    downgrade it to inline in its own parent."""
    t01 = add_subtask(s1, "Container", details="Has text").task_id
    t0101 = add_subtask(t01, "Child").task_id

    # s1 is now extended (directory) because t01 has details
    story_dir = next(tasks_root.glob(f"{s1}-*/"))
    container_file = next(story_dir.glob(f"{t01}-*.md"))
    content = container_file.read_text()
    # Remove description so container can go inline after losing subtasks
    lines = content.split("\n")
    new_lines = [line for line in lines if line != "Has text"]
    container_file.write_text("\n".join(new_lines))

    # Move the only subtask out
    assert_invoke(app, ["move", t0101, "--parent", s2])

    # Container should now be inline in s1's subtask list
    # s1 should have downgraded from extended to basic (single file)
    story_file = next(tasks_root.glob(f"{s1}-*.md"))
    story_content = story_file.read_text()
    assert "Container" in story_content
    assert f"- [ ] {t01}: Container" in story_content


# ---------------------------------------------------------------------------
# Non-move commands must NOT downgrade extended tasks
# ---------------------------------------------------------------------------


def test_done_does_not_downgrade_extended_to_basic(s1: str, tasks_root: Path) -> None:
    """Marking a subtask done must not collapse the parent directory."""
    t01 = add_subtask(s1, "Task A", details="Has details").task_id

    # s1 is extended (directory)
    src_dirs = list(tasks_root.glob(f"{s1}-*/"))
    assert len(src_dirs) == 1

    assert_invoke(app, ["done", t01])

    # s1 must still be a directory, not a flat file
    src_dirs_after = list(tasks_root.glob(f"{s1}-*/"))
    assert len(src_dirs_after) == 1
    assert src_dirs_after[0].is_dir()


def test_cancel_does_not_downgrade_extended_to_basic(s1: str, tasks_root: Path) -> None:
    """Cancelling a subtask must not collapse the parent directory."""
    t01 = add_subtask(s1, "Task A", details="Has details").task_id

    src_dirs = list(tasks_root.glob(f"{s1}-*/"))
    assert len(src_dirs) == 1

    assert_invoke(app, ["cancel", t01])

    src_dirs_after = list(tasks_root.glob(f"{s1}-*/"))
    assert len(src_dirs_after) == 1
    assert src_dirs_after[0].is_dir()


def test_start_does_not_downgrade_extended_to_basic(s1: str, tasks_root: Path) -> None:
    """Starting a subtask must not collapse the parent directory."""
    t01 = add_subtask(s1, "Task A", details="Has details").task_id

    src_dirs = list(tasks_root.glob(f"{s1}-*/"))
    assert len(src_dirs) == 1

    assert_invoke(app, ["start", t01])

    src_dirs_after = list(tasks_root.glob(f"{s1}-*/"))
    assert len(src_dirs_after) == 1
    assert src_dirs_after[0].is_dir()


def test_reset_does_not_downgrade_extended_to_basic(s1: str, tasks_root: Path) -> None:
    """Resetting a subtask must not collapse the parent directory."""
    t01 = add_subtask(s1, "Task A", details="Has details").task_id
    assert_invoke(app, ["start", t01])

    src_dirs = list(tasks_root.glob(f"{s1}-*/"))
    assert len(src_dirs) == 1

    assert_invoke(app, ["reset", t01])

    src_dirs_after = list(tasks_root.glob(f"{s1}-*/"))
    assert len(src_dirs_after) == 1
    assert src_dirs_after[0].is_dir()


def test_edit_does_not_downgrade_extended_to_basic(s1: str, tasks_root: Path) -> None:
    """Editing a subtask title must not collapse the parent directory."""
    t01 = add_subtask(s1, "Task A", details="Has details").task_id

    src_dirs = list(tasks_root.glob(f"{s1}-*/"))
    assert len(src_dirs) == 1

    assert_invoke(app, ["edit", t01, "--title", "Updated title"])

    src_dirs_after = list(tasks_root.glob(f"{s1}-*/"))
    assert len(src_dirs_after) == 1
    assert src_dirs_after[0].is_dir()


# ---------------------------------------------------------------------------
# Moved task itself downgrades to inline when eligible
# ---------------------------------------------------------------------------


def test_move_root_task_without_description_becomes_inline(
    s2: str, tasks_root: Path
) -> None:
    """A root task with no description or subtasks should become inline
    when moved under another task."""
    s1 = create_task("Simple story").task_id  # file-based, no description, no subtasks

    assert_invoke(app, ["move", s1, "--parent", s2])

    # The moved task (now s2t01) must be inline — no separate file
    new_id = f"{s2}t01"
    assert not any(
        tasks_root.rglob(f"{new_id}-*.md")
    ), f"Expected {new_id} to be inline, but a file was found"

    # Must appear as an inline bullet inside s2's file
    s2_file = next(tasks_root.glob(f"{s2}-*.md"))
    s2_content = s2_file.read_text()
    assert f"{new_id}: Simple story" in s2_content


def test_move_root_task_with_description_stays_basic(s2: str, tasks_root: Path) -> None:
    """A root task WITH description must remain file-based after being moved."""
    s1 = create_task("Story with desc").task_id
    assert_invoke(app, ["edit", s1, "--details", "Important context"])

    assert_invoke(app, ["move", s1, "--parent", s2])

    new_id = f"{s2}t01"
    assert any(
        tasks_root.rglob(f"{new_id}-*.md")
    ), f"Expected {new_id} to remain file-based, but no file was found"


def test_move_basic_subtask_without_description_becomes_inline(
    s1: str, s2: str, tasks_root: Path
) -> None:
    """A basic (file-based) subtask whose description was later cleared
    should become inline when moved to another parent."""
    t01 = add_subtask(s1, "Transient task", details="Initial description").task_id

    # Manually clear the description from the file
    s1_dir = next(tasks_root.glob(f"{s1}-*/"))
    t01_file = next(s1_dir.glob(f"{t01}-*.md"))
    content = t01_file.read_text()
    cleared = "\n".join(
        line for line in content.splitlines() if line != "Initial description"
    )
    t01_file.write_text(cleared)

    assert_invoke(app, ["move", t01, "--parent", s2])

    new_id = f"{s2}t01"
    assert not any(
        tasks_root.rglob(f"{new_id}-*.md")
    ), f"Expected {new_id} to be inline after move, but a file was found"


def test_move_basic_subtask_with_description_stays_basic(
    s1: str, s2: str, tasks_root: Path
) -> None:
    """A basic (file-based) subtask with a non-empty description must
    remain file-based after the move."""
    t01 = add_subtask(s1, "Rich task", details="Keeps description").task_id

    assert_invoke(app, ["move", t01, "--parent", s2])

    new_id = f"{s2}t01"
    assert any(
        tasks_root.rglob(f"{new_id}-*.md")
    ), f"Expected {new_id} to remain file-based, but no file was found"


# ---------------------------------------------------------------------------
# Multiple args
# ---------------------------------------------------------------------------


def test_move_multiple_tasks_to_parent(s1: str, s2: str) -> None:
    t01 = add_subtask(s1, "Task A").task_id
    t02 = add_subtask(s1, "Task B").task_id
    result = assert_invoke(app, ["move", t01, t02, "--parent", s2])
    assert "moved" in result.output
    assert s2 in result.output


def test_move_multiple_tasks_to_root(s2: str) -> None:
    t01 = add_subtask(s2, "Task A").task_id
    t02 = add_subtask(s2, "Task B").task_id
    result = assert_invoke(app, ["move", t01, t02, "--root"])
    assert "moved" in result.output


def test_move_multiple_shows_single_preview(s1: str, s2: str) -> None:
    """Preview block should appear only once at the end, not per task."""
    add_subtask(s1, "Task A")
    add_subtask(s1, "Task B")
    add_subtask(s1, "Task C")
    result = assert_invoke(
        app, ["move", f"{s1}t01", f"{s1}t02", f"{s1}t03", "--parent", s2]
    )
    # The parent header (Story two) should appear exactly once in the preview
    assert result.output.count("Story two") == 1


# ---------------------------------------------------------------------------
# show parent task on move --parent
# ---------------------------------------------------------------------------


def test_move_parent_shows_new_parent(s1: str, s2: str) -> None:
    t01 = add_subtask(s1, "Task A").task_id
    result = assert_invoke(app, ["move", t01, "--parent", s2])
    assert "Story two" in result.output


def test_move_parent_shows_moved_task_in_parent(s1: str, s2: str) -> None:
    add_subtask(s1, "Task A")
    result = assert_invoke(app, ["move", f"{s1}t01", "--parent", s2])
    assert "Task A" in result.output


def test_move_parent_shows_existing_sibling(s1: str, s2: str) -> None:
    t01 = add_subtask(s1, "Task A").task_id
    add_subtask(s2, "Pre-existing")
    result = assert_invoke(app, ["move", t01, "--parent", s2])
    assert "Pre-existing" in result.output


def test_move_root_shows_root_list(s1: str, s2: str) -> None:
    t01 = add_subtask(s1, "Task A").task_id
    result = assert_invoke(app, ["move", t01, "--root"])
    assert "Task A" in result.output


def test_move_root_no_subtasks_in_list(s1: str) -> None:
    add_subtask(s1, "Task A")
    add_subtask(s1, "Task B")
    result = assert_invoke(app, ["move", f"{s1}t01", "--root"])
    # subtasks of s1 are not shown (flat root list only)
    assert "Task B" not in result.output


def test_move_parent_json_no_preview(s1: str, s2: str) -> None:
    t01 = add_subtask(s1, "Task A").task_id
    result = assert_invoke(app, ["--json-output", "move", t01, "--parent", s2])
    data = json.loads(result.output)
    assert "task_refs" in data
    assert "parent" not in data


# ---------------------------------------------------------------------------
# deep nested detach cleans ancestor directories
# ---------------------------------------------------------------------------


def test_move_deep_nested_cleans_ancestor_dirs(tasks_root: Path, s1: str) -> None:
    t01 = add_subtask(s1, "Mid task").task_id
    # file-based subtask makes s01t01 extended (directory-based)
    leaf = add_subtask(t01, "Leaf task", details="Some details").task_id
    assert_invoke(app, ["move", leaf, "--root"])
    # all intermediate directories should be cleaned up
    leftover = [p for p in tasks_root.rglob("*") if p.is_dir() and p.name != "archive"]
    dirs = [str(p.relative_to(tasks_root)) for p in leftover]
    assert dirs == [], f"Leftover directories: {dirs}"


def test_move_deep_nested_to_parent_cleans_dirs(
    tasks_root: Path, s1: str, s2: str
) -> None:
    t01 = add_subtask(s1, "Mid task").task_id
    leaf = add_subtask(t01, "Leaf task", details="Some details").task_id
    assert_invoke(app, ["move", leaf, "--parent", s2])
    # s01's intermediate directory should be cleaned up
    for p in tasks_root.rglob("*"):
        if p.is_dir():
            assert f"{s1}t01" not in p.name, f"Leftover directory: {p}"


def test_move_deep_nested_to_parent_keeps_dirs(
    tasks_root: Path, s1: str, s2: str
) -> None:
    t01 = add_subtask(s1, "Mid task").task_id
    leaf1 = add_subtask(t01, "Leaf task 1", details="Some details").task_id
    add_subtask(t01, "Leaf task 2", details="Some details").task_id
    assert_invoke(app, ["move", leaf1, "--parent", s2])
    # s01's intermediate directory should remain
    dirs = [p for p in tasks_root.rglob("*") if p.is_dir()]
    assert any(t01 in p.name for p in dirs), f"Missing {t01} dir"


# ---------------------------------------------------------------------------
# move --delete
# ---------------------------------------------------------------------------


def test_delete_inline_subtask(s1: str, get_task_file: GetTaskFile) -> None:
    add_subtask(s1, "Task A")
    add_subtask(s1, "Task B")
    result = assert_invoke(app, ["move", f"{s1}t01", "--delete"])
    assert "deleted" in result.output

    content = get_task_file(s1).read_text()
    assert "Task A" not in content
    assert "Task B" in content


def test_delete_file_subtask(s1: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Task A", details="Has details").task_id
    story_dir = next(tasks_root.glob(f"{s1}-*/"))
    old_file = next(story_dir.glob(f"{t01}-*.md"))
    assert old_file.exists()

    result = assert_invoke(app, ["move", t01, "--delete"])
    assert "deleted" in result.output
    assert not old_file.exists()


def test_delete_extended_subtask(s1: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Container", details="Details").task_id
    add_subtask(t01, "Child", details="Child details")
    story_dir = next(tasks_root.glob(f"{s1}-*/"))
    old_dir = next(story_dir.glob(f"{t01}-*/"))
    assert old_dir.is_dir()

    assert_invoke(app, ["move", t01, "--delete"])
    assert not old_dir.exists()


def test_delete_root_task(s1: str, tasks_root: Path) -> None:
    old_file = next(tasks_root.glob(f"{s1}-*.md"))
    assert old_file.exists()

    result = assert_invoke(app, ["move", s1, "--delete"])
    assert "deleted" in result.output
    assert not old_file.exists()


def test_delete_multiple_tasks(s1: str) -> None:
    add_subtask(s1, "Task A")
    add_subtask(s1, "Task B")
    result = assert_invoke(app, ["move", f"{s1}t01", f"{s1}t02", "--delete"])
    assert "deleted" in result.output


def test_delete_json_output(s1: str) -> None:
    add_subtask(s1, "Task A")
    result = assert_invoke(app, ["--json-output", "move", f"{s1}t01", "--delete"])
    data = json.loads(result.output)
    assert "task_refs" in data


def test_delete_parent_downgrades(s1: str, tasks_root: Path) -> None:
    """Deleting the only file-based subtask should downgrade parent."""
    t01 = add_subtask(s1, "File task", details="Has details").task_id

    src_dirs = list(tasks_root.glob(f"{s1}-*/"))
    assert len(src_dirs) == 1
    assert src_dirs[0].is_dir()

    assert_invoke(app, ["move", t01, "--delete"])

    # source should downgrade to basic file
    src_files = list(tasks_root.glob(f"{s1}-*.md"))
    assert len(src_files) == 1
    assert src_files[0].is_file()


def test_delete_rejects_with_parent_flag(s1: str, s2: str) -> None:
    t01 = add_subtask(s1, "Task").task_id
    result = assert_invoke(
        app, ["move", t01, "--delete", "--parent", s2], expect_error=True
    )
    assert "only one" in result.output.lower()


def test_delete_rejects_with_root_flag(s1: str) -> None:
    t01 = add_subtask(s1, "Task").task_id
    result = assert_invoke(app, ["move", t01, "--delete", "--root"], expect_error=True)
    assert "only one" in result.output.lower()


def test_delete_shows_preview_with_parent(s1: str) -> None:
    """Deleting a subtask should show the parent preview with deleted task."""
    add_subtask(s1, "Task A")
    add_subtask(s1, "Task B")
    result = assert_invoke(app, ["move", f"{s1}t01", "--delete"])
    # preview should show parent with remaining and deleted tasks
    assert "Story one" in result.output
    assert "Task A" in result.output
    assert "Task B" in result.output


def test_delete_preview_not_listed_as_subtask_text(s1: str) -> None:
    """No 'Deleted subtasks:' section — preview handles it."""
    add_subtask(s1, "Task A")
    result = assert_invoke(app, ["move", f"{s1}t01", "--delete"])
    assert "Deleted subtasks:" not in result.output


# ---------------------------------------------------------------------------
# move --editor
# ---------------------------------------------------------------------------


def test_move_editor_calls_editor(s1: str, s2: str, run_editor: mock.Mock) -> None:
    t01 = add_subtask(s1, "Task A").task_id
    assert_invoke(app, ["move", t01, "--parent", s2, "--editor"])
    assert run_editor.call_count == 1


def test_move_editor_short_flag(s1: str, s2: str, run_editor: mock.Mock) -> None:
    t01 = add_subtask(s1, "Task A").task_id
    assert_invoke(app, ["move", t01, "--parent", s2, "-e"])
    assert run_editor.call_count == 1


def test_move_editor_opens_moved_task(s1: str, s2: str, run_editor: mock.Mock) -> None:
    t01 = add_subtask(s1, "Task A").task_id
    assert_invoke(app, ["move", t01, "--parent", s2, "-e"])
    opened_path: Path = run_editor.call_args[0][0]
    assert opened_path.exists()
    content = opened_path.read_text()
    assert "Task A" in content


def test_move_root_editor_opens_promoted_task(s1: str, run_editor: mock.Mock) -> None:
    t01 = add_subtask(s1, "Task A", details="some desc").task_id
    assert_invoke(app, ["move", t01, "--root", "-e"])
    opened_path: Path = run_editor.call_args[0][0]
    assert opened_path.exists()
    content = opened_path.read_text()
    assert "Task A" in content


def test_move_editor_opens_each_moved_task(
    s1: str, s2: str, run_editor: mock.Mock
) -> None:
    add_subtask(s1, "Task A")
    add_subtask(s1, "Task B")
    assert_invoke(app, ["move", f"{s1}t01", f"{s1}t02", "--parent", s2, "-e"])
    assert run_editor.call_count == 2


def test_move_delete_editor_errors(s1: str) -> None:
    add_subtask(s1, "Task A")
    result = assert_invoke(
        app, ["move", f"{s1}t01", "--delete", "-e"], expect_error=True
    )
    assert "--editor cannot be used with --delete" in result.output
