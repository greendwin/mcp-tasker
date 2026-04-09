import json
from pathlib import Path

import pytest

from tasker.base_types import TaskStatus
from tasker.cli import app
from tasker.layout import ARCHIVE_DIR
from tasker.parse import parse_task_file
from tasker.repo import TaskRepo
from tasker.todo import load_todo_ids

from .helpers import GetTaskFile, add_subtask, assert_invoke, create_task


@pytest.fixture()
def story_id() -> str:
    return create_task("My story").task_id


@pytest.fixture()
def repo(tasks_root: Path) -> TaskRepo:
    return TaskRepo(tasks_root)


# --- basic archive ---


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


# --- task must be closed ---


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


# --- --force cancels open subtasks ---


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


# --- JSON output ---


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


# --- new task ID must not collide with archived IDs ---


def test_new_task_skips_archived_ids(story_id: str) -> None:
    assert_invoke(app, ["done", "--force", story_id])
    assert_invoke(app, ["archive", story_id])

    # create a new task — its ID must be higher than the archived one
    new = create_task("Second story")
    assert new.task_id > story_id


# --- actions on archived tasks work transparently ---


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


# --- unarchive command ---


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


# --- unarchive shows preview ---


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


# --- move archived task / to archived parent ---


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


# --- --closed flag ---


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


# --- auto-remove from .todo on archive ---


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
