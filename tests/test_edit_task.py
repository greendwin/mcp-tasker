import json
import platform
import subprocess
from pathlib import Path
from typing import Protocol
from unittest import mock

import pytest

from tasker.cli import _task_commands, app
from tasker.parse import parse_task_file

from .conftest import GetTaskFile
from .helpers import add_subtask, assert_invoke, create_task

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def s1() -> str:
    return create_task("Story one").task_id


# ---------------------------------------------------------------------------
# Edit details (s14t01)
# ---------------------------------------------------------------------------


def test_edit_details_on_file_task(s1: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Task A", details="Old details").task_id
    assert_invoke(app, ["edit", t01, "--details", "New details"])

    story_dir = next(tasks_root.glob(f"{s1}-*/"))
    task_file = next(story_dir.glob(f"{t01}-*.md"))
    parsed = parse_task_file(task_file)
    assert parsed.task.description == "New details"


def test_edit_details_capitalizes_first_letter(s1: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Task A", details="old details").task_id
    assert_invoke(app, ["edit", t01, "--details", "new description"])

    story_dir = next(tasks_root.glob(f"{s1}-*/"))
    task_file = next(story_dir.glob(f"{t01}-*.md"))
    parsed = parse_task_file(task_file)
    assert parsed.task.description == "New description"


def test_edit_details_on_root_task(s1: str, get_task_file: GetTaskFile) -> None:
    assert_invoke(app, ["edit", s1, "--details", "Root description"])

    task_file = get_task_file(s1)
    parsed = parse_task_file(task_file)
    assert parsed.task.description == "Root description"


def test_edit_details_upgrades_inline_task(
    s1: str, tasks_root: Path, get_task_file: GetTaskFile
) -> None:
    t01 = add_subtask(s1, "Inline task").task_id

    # before: parent is a basic .md file (no directory)
    old_file = get_task_file(s1)
    assert old_file.is_file()

    assert_invoke(app, ["edit", t01, "--details", "Now has details"])

    # after: parent upgraded to extended (directory with README.md)
    story_dir = next(tasks_root.glob(f"{s1}-*/"))
    assert story_dir.is_dir()
    assert (story_dir / "README.md").exists()

    # child is now file-backed
    task_file = next(story_dir.glob(f"{t01}-*.md"))
    parsed = parse_task_file(task_file)
    assert parsed.task.description == "Now has details"


# ---------------------------------------------------------------------------
# Edit title (s14t02)
# ---------------------------------------------------------------------------


def test_edit_title(s1: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Old title", details="Details").task_id
    assert_invoke(app, ["edit", t01, "--title", "new title"])

    story_dir = next(tasks_root.glob(f"{s1}-*/"))
    task_file = next(story_dir.glob(f"{t01}-*.md"))
    parsed = parse_task_file(task_file)
    assert parsed.task.title == "New title"  # auto-capitalized


def test_edit_title_on_inline_task(s1: str, get_task_file: GetTaskFile) -> None:
    t01 = add_subtask(s1, "Old title").task_id
    assert_invoke(app, ["edit", t01, "--title", "updated title"])

    task_file = get_task_file(s1)
    content = task_file.read_text()
    assert "Updated title" in content


def test_edit_title_updates_parent_subtask_list(s1: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Old title", details="Details").task_id
    assert_invoke(app, ["edit", t01, "--title", "brand new title"])

    # parent README should reference the new title
    story_dir = next(tasks_root.glob(f"{s1}-*/"))
    readme = story_dir / "README.md"
    content = readme.read_text()
    assert "Brand new title" in content


# ---------------------------------------------------------------------------
# Edit slug (s14t03)
# ---------------------------------------------------------------------------


def test_edit_slug(s1: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Task A", details="Details").task_id
    assert_invoke(app, ["edit", t01, "--slug", "new-slug"])

    story_dir = next(tasks_root.glob(f"{s1}-*/"))
    new_files = list(story_dir.glob(f"{t01}-new-slug.md"))
    assert len(new_files) == 1


def test_edit_slug_removes_old_file(s1: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Task A", details="Details").task_id
    story_dir = next(tasks_root.glob(f"{s1}-*/"))
    old_file = next(story_dir.glob(f"{t01}-*.md"))
    old_path = old_file.resolve()

    assert_invoke(app, ["edit", t01, "--slug", "renamed"])
    assert not old_path.exists()


def test_edit_slug_upgrades_inline_task_and_parent(
    s1: str, tasks_root: Path, get_task_file: GetTaskFile
) -> None:
    t01 = add_subtask(s1, "Inline task").task_id

    # before: parent is a basic .md file
    old_file = get_task_file(s1)
    assert old_file.is_file()

    assert_invoke(app, ["edit", t01, "--slug", "custom-slug"])

    # after: parent upgraded to extended (directory with README.md)
    story_dir = next(tasks_root.glob(f"{s1}-*/"))
    assert story_dir.is_dir()
    assert (story_dir / "README.md").exists()

    # child is now file-backed with the custom slug
    task_file = next(story_dir.glob(f"{t01}-custom-slug.md"))
    assert task_file.exists()


# ---------------------------------------------------------------------------
# Multiple fields at once
# ---------------------------------------------------------------------------


def test_edit_multiple_fields(s1: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Task A", details="Old details").task_id
    assert_invoke(
        app, ["edit", t01, "--title", "new title", "--details", "New details"]
    )

    story_dir = next(tasks_root.glob(f"{s1}-*/"))
    task_file = next(story_dir.glob(f"{t01}-*.md"))
    parsed = parse_task_file(task_file)
    assert parsed.task.title == "New title"
    assert parsed.task.description == "New details"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_edit_no_flags_fails(s1: str) -> None:
    result = assert_invoke(app, ["edit", s1], expect_error=True)
    assert "at least one" in result.output.lower() or "error" in result.output.lower()


def test_edit_nonexistent_task_fails() -> None:
    assert_invoke(app, ["edit", "s99", "--title", "X"], expect_error=True)


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------


def test_edit_json_output(s1: str) -> None:
    result = assert_invoke(app, ["--json-output", "edit", s1, "--title", "Updated"])
    data = json.loads(result.output)
    assert "task_ref" in data


def test_edit_json_error(s1: str) -> None:
    result = assert_invoke(app, ["--json-output", "edit", s1], expect_error=True)
    data = json.loads(result.output)
    assert "error" in data


# ---------------------------------------------------------------------------
# Editor
# ---------------------------------------------------------------------------


open_in_editor_orig = _task_commands.open_in_editor


class SetupEditors(Protocol):
    def __call__(
        self, *, system: str | None = None, visual: str | None, editor: str | None
    ) -> mock.Mock: ...


@pytest.fixture
def setup_editors(monkeypatch: pytest.MonkeyPatch) -> SetupEditors:
    def callback(
        *, system: str | None = None, visual: str | None, editor: str | None
    ) -> mock.Mock:
        subprocess_run = mock.Mock(return_value=None)
        monkeypatch.setattr(subprocess, "run", subprocess_run)

        if system is not None:
            monkeypatch.setattr(platform, "system", lambda: system)

        if visual:
            monkeypatch.setenv("VISUAL", visual)
        else:
            monkeypatch.delenv("VISUAL", raising=False)

        if editor:
            monkeypatch.setenv("EDITOR", editor)
        else:
            monkeypatch.delenv("EDITOR", raising=False)

        return subprocess_run

    return callback


def test_edit_editor_uses_visual_env_var(s1: str, setup_editors: SetupEditors) -> None:
    subprocess_run = setup_editors(visual="emacs", editor="vim")

    open_in_editor_orig(Path(s1))
    subprocess_run.assert_called_once_with(["emacs", s1])


def test_edit_editor_uses_editor_env_var(s1: str, setup_editors: SetupEditors) -> None:
    subprocess_run = setup_editors(visual=None, editor="nano")

    open_in_editor_orig(Path(s1))
    subprocess_run.assert_called_once_with(["nano", s1])


def test_edit_editor_fallback_linux(s1: str, setup_editors: SetupEditors) -> None:
    subprocess_run = setup_editors(system="Linux", visual=None, editor=None)

    open_in_editor_orig(Path(s1))
    subprocess_run.assert_called_once_with(["vi", s1])


def test_edit_editor_fallback_windows(s1: str, setup_editors: SetupEditors) -> None:
    subprocess_run = setup_editors(system="Windows", visual=None, editor=None)

    open_in_editor_orig(Path(s1))
    subprocess_run.assert_called_once_with(["notepad", s1])


def test_edit_editor_alone_is_valid(s1: str, open_in_editor: mock.Mock) -> None:
    assert_invoke(app, ["edit", s1, "--editor"])
    assert open_in_editor.call_count == 1


def test_edit_editor_short_flag(s1: str, open_in_editor: mock.Mock) -> None:
    assert_invoke(app, ["edit", s1, "-e"])
    assert open_in_editor.call_count == 1


def test_edit_editor_opens_correct_file(s1: str, open_in_editor: mock.Mock) -> None:
    assert_invoke(app, ["edit", s1, "--editor"])
    opened_path = open_in_editor.call_args[0][0]
    assert str(opened_path).endswith(".md")


def test_edit_editor_upgrades_inline_task(
    s1: str, tasks_root: Path, open_in_editor: mock.Mock
) -> None:
    t01 = add_subtask(s1, "Inline task").task_id

    # before: s1 is a basic .md (no dir), t01 is inline
    old_file = next(tasks_root.glob(f"{s1}-*.md"))
    assert old_file.is_file()

    assert_invoke(app, ["edit", t01, "--editor"])

    # after: s1 upgraded to extended dir, t01 has its own file
    story_dir = next(tasks_root.glob(f"{s1}-*/"))
    assert story_dir.is_dir()
    assert (story_dir / "README.md").exists()
    task_filename = list(story_dir.glob(f"{t01}-*.md"))
    assert len(task_filename) == 1

    expected_path = story_dir / task_filename[0]
    open_in_editor.assert_called_once_with(expected_path)


def test_edit_editor_applies_changes_before_opening(
    s1: str, open_in_editor: mock.Mock
) -> None:
    opened_contents: list[str] = []

    def fake_open(path: Path) -> None:
        opened_contents.append(path.read_text())

    open_in_editor.side_effect = fake_open

    assert_invoke(app, ["edit", s1, "--title", "Changed title", "--editor"])

    assert len(opened_contents) == 1
    assert "Changed title" in opened_contents[0]


def test_edit_editor_combined_with_other_flags(
    s1: str, tasks_root: Path, open_in_editor: mock.Mock
) -> None:
    assert_invoke(app, ["edit", s1, "--title", "New title", "--editor"])

    task_file = next(tasks_root.glob(f"{s1}-*.md"))
    content = task_file.read_text()
    assert "New title" in content
    assert open_in_editor.call_count == 1
