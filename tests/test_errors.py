import os
from pathlib import Path

import pytest

from tasker.cli import app
from tasker.exceptions import TaskerError

from .helpers import assert_invoke


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
