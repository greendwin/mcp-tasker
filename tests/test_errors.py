import pytest

from tasker.cli import app
from tasker.exceptions import TaskerError

from .helpers import assert_invoke


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
