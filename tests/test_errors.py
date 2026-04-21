import json
import os
from pathlib import Path

import pytest
from pyfakefs.fake_filesystem import FakeFilesystem

from tasker.cli import app
from tasker.exceptions import TaskerError
from tasker.repo import TaskRepo
from tasker.utils import read_text, write_text

from .helpers import assert_invoke, create_task


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
