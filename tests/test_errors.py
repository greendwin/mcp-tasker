import json
import os
from pathlib import Path

import pytest
from pyfakefs.fake_filesystem import FakeFilesystem

from tasker.cli import app
from tasker.exceptions import TaskerError
from tasker.parse import parse_task_ref
from tasker.repo import TaskRepo
from tasker.utils import read_text, write_text

from .helpers import add_subtask, assert_invoke, create_task


def test_tasker_not_found_shows_clean_message() -> None:
    bare = Path("/no-tasker")
    bare.mkdir()
    os.chdir(bare)
    result = assert_invoke(app, ["list"], expect_error=True)
    assert "Error:" in result.output
    assert "Tasker directory not found" in result.output
    assert "Traceback" not in result.output


def test_tasker_not_found_debug_propagates_exception() -> None:
    bare = Path("/no-tasker-debug")
    bare.mkdir()
    os.chdir(bare)
    with pytest.raises(TaskerError):
        assert_invoke(app, ["--debug", "list"])


def test_tasker_not_found_json_output() -> None:
    bare = Path("/no-tasker-json")
    bare.mkdir()
    os.chdir(bare)
    result = assert_invoke(app, ["--json-output", "list"], expect_error=True)
    assert "Tasker directory not found" in result.output
    assert "tasker_not_found" in result.output


def test_tasker_error_shows_clean_message() -> None:
    result = assert_invoke(app, ["add", "s99", "Some task"], expect_error=True)
    assert "Error:" in result.output


def test_tasker_error_no_traceback_by_default() -> None:
    result = assert_invoke(app, ["add", "s99", "Some task"], expect_error=True)
    assert "Traceback" not in result.output


def test_tasker_error_escapes_markup_in_message() -> None:
    result = assert_invoke(app, ["show", "[red]bad[/red]"], expect_error=True)
    assert "[red]bad[/red]" in result.output


def test_debug_flag_propagates_exception() -> None:
    with pytest.raises(TaskerError):
        assert_invoke(app, ["--debug", "add", "s99", "Some task"])


def test_debug_flag_does_not_print_clean_error() -> None:
    with pytest.raises(TaskerError):
        assert_invoke(app, ["--debug", "add", "s99", "Some task"])


def test_read_text_missing_file_raises_tasker_error() -> None:
    missing = Path("/nonexistent/file.md")
    with pytest.raises(TaskerError) as exc_info:
        read_text(missing)
    assert exc_info.value.file_path == missing


def test_write_text_unwritable_raises_tasker_error(fs: FakeFilesystem) -> None:
    target = Path("/readonly/file.md")
    target.parent.mkdir(parents=True)
    fs.chmod(str(target.parent), 0o444)
    with pytest.raises(TaskerError) as exc_info:
        write_text(target, "content")
    assert exc_info.value.file_path == target


def test_generic_exception_no_traceback_without_debug(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _boom(self: object, *, archived: bool = False) -> list[Path]:
        raise RuntimeError("boom")

    monkeypatch.setattr(TaskRepo, "list_root_tasks", _boom)
    result = assert_invoke(app, ["list"], expect_error=True)
    assert "Error:" in result.output
    assert "boom" in result.output
    assert "Traceback" not in result.output


def test_generic_exception_json_no_traceback_without_debug(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _boom(self: object, *, archived: bool = False) -> list[Path]:
        raise RuntimeError("boom")

    monkeypatch.setattr(TaskRepo, "list_root_tasks", _boom)
    result = assert_invoke(app, ["--json-output", "list"], expect_error=True)
    data = json.loads(result.output)
    assert data["error"] == "boom"
    assert "traceback" not in data


def test_generic_exception_json_has_traceback_with_debug(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _boom(self: object, *, archived: bool = False) -> list[Path]:
        raise RuntimeError("boom")

    monkeypatch.setattr(TaskRepo, "list_root_tasks", _boom)
    result = assert_invoke(app, ["--json-output", "--debug", "list"], expect_error=True)
    data = json.loads(result.output)
    assert data["error"] == "boom"
    assert "traceback" in data
    assert "RuntimeError" in data["traceback"]


def test_generic_exception_debug_propagates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _boom(self: object, *, archived: bool = False) -> list[Path]:
        raise RuntimeError("boom")

    monkeypatch.setattr(TaskRepo, "list_root_tasks", _boom)
    with pytest.raises(RuntimeError, match="boom"):
        assert_invoke(app, ["--debug", "list"])


def test_list_warns_on_missing_readme_in_root_task_dir(tasks_root: Path) -> None:
    create_task("Good story")
    # create a directory that looks like a task but has no README.md
    broken_dir = tasks_root / "s02-broken-story"
    broken_dir.mkdir()
    result = assert_invoke(app, ["list"])
    assert "Warning:" in result.output
    assert "s02-broken-story/README.md" in result.output
    assert "Good story" in result.output


def test_list_warns_on_missing_readme_in_subtask_dir(tasks_root: Path) -> None:
    # create an extended root task (directory-based)
    result = assert_invoke(app, ["--json-output", "new", "--extended", "Parent story"])
    ref = parse_task_ref(json.loads(result.output.strip())["task_ref"])
    add_subtask(ref.task_id, "Good subtask")
    # create a directory that looks like a subtask but has no README.md
    parent_dir = tasks_root / ref.task_ref
    subtask_dir = parent_dir / f"{ref.task_id}t99-broken-subtask"
    subtask_dir.mkdir()
    # add the subtask reference to the parent README.md
    readme = parent_dir / "README.md"
    content = readme.read_text()
    broken_ref = f"{ref.task_id}t99"
    content += (
        f"\n- [ ] [{broken_ref}]" f"({broken_ref}-broken-subtask/): Broken subtask\n"
    )
    readme.write_text(content)
    result = assert_invoke(app, ["list"])
    assert "Warning:" in result.output
    assert "broken-subtask/README.md" in result.output
    assert "Parent story" in result.output


def test_list_json_skips_missing_readme_silently(tasks_root: Path) -> None:
    create_task("Good story")
    broken_dir = tasks_root / "s02-broken-story"
    broken_dir.mkdir()
    result = assert_invoke(app, ["--json-output", "list"])
    data = json.loads(result.output)
    assert "Warning" not in result.output
    ids = [t["id"] for t in data["tasks"]]
    assert "s02" not in ids


def test_show_broken_task_dir_still_errors(tasks_root: Path) -> None:
    broken_dir = tasks_root / "s01-broken-story"
    broken_dir.mkdir()
    result = assert_invoke(app, ["show", "s01"], expect_error=True)
    assert "Error:" in result.output
    assert "README.md" in result.output


def test_malformed_task_shows_file_path(tasks_root: Path) -> None:
    ref = create_task("Broken story")
    task_file = next(tasks_root.glob(f"{ref.task_id}-*.md"))
    task_file.write_text("not valid front-matter")
    result = assert_invoke(app, ["show", ref.task_id], expect_error=True)
    assert task_file.name in result.output


def test_malformed_task_path_is_relative(tasks_root: Path) -> None:
    ref = create_task("Broken story")
    task_file = next(tasks_root.glob(f"{ref.task_id}-*.md"))
    task_file.write_text("not valid front-matter")
    result = assert_invoke(app, ["show", ref.task_id], expect_error=True)
    # path should be relative to tasker dir, not absolute
    assert str(tasks_root) not in result.output
