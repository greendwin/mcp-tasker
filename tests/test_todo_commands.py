import json
from pathlib import Path

import pytest

from tasker.cli import app
from tasker.repo import TaskRepo
from tasker.todo import load_todo_ids

from .helpers import add_subtask, assert_invoke, create_task


@pytest.fixture()
def story_id() -> str:
    return create_task("My story").task_id


@pytest.fixture()
def repo(tasks_root: Path) -> TaskRepo:
    return TaskRepo(tasks_root)


# --- todo command ---


def test_todo_adds_task(story_id: str, repo: TaskRepo) -> None:
    assert_invoke(app, ["todo", story_id])
    assert story_id in load_todo_ids(repo)


def test_todo_prints_confirmation(story_id: str) -> None:
    result = assert_invoke(app, ["todo", story_id])
    assert "added to todo" in result.output


def test_todo_idempotent(story_id: str) -> None:
    assert_invoke(app, ["todo", story_id])
    result = assert_invoke(app, ["todo", story_id])
    assert "already in todo" in result.output


def test_todo_multiple_tasks(story_id: str, repo: TaskRepo) -> None:
    t01 = add_subtask(story_id, "Task one").task_id
    t02 = add_subtask(story_id, "Task two").task_id
    assert_invoke(app, ["todo", t01, t02])
    ids = load_todo_ids(repo)
    assert t01 in ids
    assert t02 in ids


def test_todo_subtask_stores_task_id(story_id: str, repo: TaskRepo) -> None:
    t01 = add_subtask(story_id, "Subtask one").task_id
    assert_invoke(app, ["todo", t01])
    ids = load_todo_ids(repo)
    assert t01 in ids


def test_todo_nonexistent_task_fails() -> None:
    assert_invoke(app, ["todo", "s99t01"], expect_error=True)


def test_todo_json_output(story_id: str) -> None:
    result = assert_invoke(app, ["--json-output", "todo", story_id])
    data = json.loads(result.output)
    assert data["task_refs"] == [f"{story_id}-my-story"]


def test_todo_creates_gitignore_entry(story_id: str, tasks_root: Path) -> None:
    gitignore = tasks_root / ".gitignore"
    text = gitignore.read_text()
    gitignore.write_text(text.replace(".todo\n", ""))
    assert ".todo" not in gitignore.read_text()

    assert_invoke(app, ["todo", story_id])
    assert ".todo" in gitignore.read_text()


def test_todo_with_recent_shortcut(story_id: str, repo: TaskRepo) -> None:
    assert_invoke(app, ["view", story_id])
    assert_invoke(app, ["todo", "q"])
    assert story_id in load_todo_ids(repo)


def test_todo_shows_parent_preview(story_id: str) -> None:
    result = assert_invoke(app, ["todo", story_id])
    assert "My story" in result.output


# --- untodo command ---


def test_untodo_removes_task(story_id: str, repo: TaskRepo) -> None:
    assert_invoke(app, ["todo", story_id])
    assert_invoke(app, ["untodo", story_id])
    assert story_id not in load_todo_ids(repo)


def test_untodo_prints_confirmation(story_id: str) -> None:
    assert_invoke(app, ["todo", story_id])
    result = assert_invoke(app, ["untodo", story_id])
    assert "removed from todo" in result.output


def test_untodo_idempotent(story_id: str) -> None:
    result = assert_invoke(app, ["untodo", story_id])
    assert "was not in todo" in result.output


def test_untodo_nonexistent_task_fails() -> None:
    assert_invoke(app, ["untodo", "s99t01"], expect_error=True)


def test_untodo_json_output(story_id: str) -> None:
    assert_invoke(app, ["todo", story_id])
    result = assert_invoke(app, ["--json-output", "untodo", story_id])
    data = json.loads(result.output)
    assert data["task_refs"] == [f"{story_id}-my-story"]


def test_untodo_removes_file_when_empty(story_id: str, tasks_root: Path) -> None:
    assert_invoke(app, ["todo", story_id])
    assert (tasks_root / ".todo").exists()
    assert_invoke(app, ["untodo", story_id])
    assert not (tasks_root / ".todo").exists()


# --- (todo) marker in list ---


def test_list_shows_todo_marker(story_id: str) -> None:
    assert_invoke(app, ["todo", story_id])
    result = assert_invoke(app, ["list"])
    assert "(todo)" in result.output


def test_list_no_todo_marker_without_todo(story_id: str) -> None:
    result = assert_invoke(app, ["list"])
    assert "(todo)" not in result.output


def test_list_todo_marker_not_on_children(story_id: str) -> None:
    t01 = add_subtask(story_id, "Child task").task_id
    assert_invoke(app, ["todo", story_id])
    result = assert_invoke(app, ["list"])
    # marker should be on the story line, not the child line
    for line in result.output.splitlines():
        if t01 in line:
            assert "(todo)" not in line


def test_view_shows_todo_marker(story_id: str) -> None:
    assert_invoke(app, ["todo", story_id])
    result = assert_invoke(app, ["view", story_id])
    assert "(todo)" in result.output


def test_list_todo_and_recent_markers_coexist(story_id: str) -> None:
    assert_invoke(app, ["todo", story_id])
    assert_invoke(app, ["view", story_id])
    result = assert_invoke(app, ["list"])
    for line in result.output.splitlines():
        if story_id in line:
            assert "(todo)" in line
            assert "(q)" in line
            # (todo) before (q)
            assert line.index("(todo)") < line.index("(q)")


# --- .todo file format ---


def test_todo_file_sorted_by_id(story_id: str, tasks_root: Path) -> None:
    t01 = add_subtask(story_id, "Task one").task_id
    t02 = add_subtask(story_id, "Task two").task_id
    assert_invoke(app, ["todo", t02])
    assert_invoke(app, ["todo", t01])
    content = (tasks_root / ".todo").read_text()
    lines = [line for line in content.splitlines() if line.strip()]
    assert lines == sorted(lines)


# --- list --todo ---


def test_list_todo_shows_todo_tasks(story_id: str) -> None:
    assert_invoke(app, ["todo", story_id])
    result = assert_invoke(app, ["list", "--todo"])
    assert story_id in result.output
    assert "My story" in result.output


def test_list_todo_empty_shows_no_tasks() -> None:
    result = assert_invoke(app, ["list", "--todo"])
    assert "No tasks to show" in result.output


def test_list_todo_shows_parent_context(story_id: str) -> None:
    t01 = add_subtask(story_id, "Child task").task_id
    assert_invoke(app, ["todo", t01])
    result = assert_invoke(app, ["list", "--todo"])
    # parent story shown as context
    assert story_id in result.output
    assert t01 in result.output


def test_list_todo_merges_common_parents(story_id: str) -> None:
    t01 = add_subtask(story_id, "Task one").task_id
    t02 = add_subtask(story_id, "Task two").task_id
    assert_invoke(app, ["todo", t01, t02])
    result = assert_invoke(app, ["list", "--todo"])
    # parent line appears once, both children shown
    parent_lines = [
        line for line in result.output.splitlines() if line.startswith(story_id)
    ]
    assert len(parent_lines) == 1
    assert t01 in result.output
    assert t02 in result.output


def test_list_todo_with_task_refs(story_id: str) -> None:
    s2 = create_task("Other story").task_id
    assert_invoke(app, ["todo", story_id])
    result = assert_invoke(app, ["list", "--todo", s2])
    assert story_id in result.output
    assert s2 in result.output


def test_list_todo_and_archived_combined(story_id: str) -> None:
    assert_invoke(app, ["todo", story_id])
    result = assert_invoke(app, ["list", "--todo", "--archived"])
    assert story_id in result.output


def test_list_todo_no_highlight_marker(story_id: str) -> None:
    assert_invoke(app, ["todo", story_id])
    result = assert_invoke(app, ["list", "--todo"])
    assert "<<<" not in result.output


def test_list_todo_json_output(story_id: str) -> None:
    assert_invoke(app, ["todo", story_id])
    result = assert_invoke(app, ["--json-output", "list", "--todo"])
    data = json.loads(result.output)
    task_ids = [t["id"] for t in data["tasks"]]
    assert story_id in task_ids
