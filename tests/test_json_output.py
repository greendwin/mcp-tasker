import json
from typing import Any

from tasker.cli import app

from .helpers import assert_invoke


def _parse_json(output: str) -> Any:
    return json.loads(output.strip())


# --- success cases ---


def test_json_new_task_outputs_valid_json() -> None:
    result = assert_invoke(app, ["--json-output", "new", "My task"])
    _parse_json(result.output)  # must not raise


def test_json_new_task_is_single_object() -> None:
    result = assert_invoke(app, ["--json-output", "new", "My task"])
    data = _parse_json(result.output)
    assert isinstance(data, dict)


def test_json_new_task_ref_is_correct() -> None:
    result = assert_invoke(app, ["--json-output", "new", "My task"])
    data = _parse_json(result.output)
    assert "task_ref" in data
    assert data["task_ref"] == "s01-my-task"


def test_json_new_task_no_extra_output() -> None:
    result = assert_invoke(app, ["--json-output", "new", "My task"])
    # entire output must be parseable as a single JSON value
    _parse_json(result.output)
    assert "[green]" not in result.output
    assert "[blue]" not in result.output


def test_json_add_task_outputs_valid_json() -> None:
    assert_invoke(app, ["new", "Parent story"])
    result = assert_invoke(app, ["--json-output", "add", "s01", "Subtask"])
    _parse_json(result.output)  # must not raise


def test_json_add_task_is_single_object() -> None:
    assert_invoke(app, ["new", "Parent story"])
    result = assert_invoke(app, ["--json-output", "add", "s01", "Subtask"])
    data = _parse_json(result.output)
    assert isinstance(data, dict)


def test_json_add_task_ref_is_correct() -> None:
    assert_invoke(app, ["new", "Parent story"])
    result = assert_invoke(app, ["--json-output", "add", "s01", "Subtask"])
    data = _parse_json(result.output)
    assert "task_ref" in data
    assert data["task_ref"] == "s01t01"


def test_json_add_task_no_extra_output() -> None:
    assert_invoke(app, ["new", "Parent story"])
    result = assert_invoke(app, ["--json-output", "add", "s01", "Subtask"])
    _parse_json(result.output)
    assert "[green]" not in result.output
    assert "[blue]" not in result.output


# --- error cases ---


def test_json_error_outputs_valid_json() -> None:
    result = assert_invoke(
        app, ["--json-output", "add", "s99", "Task"], expect_error=True
    )
    _parse_json(result.output)  # must not raise


def test_json_error_is_single_object() -> None:
    result = assert_invoke(
        app, ["--json-output", "add", "s99", "Task"], expect_error=True
    )
    data = _parse_json(result.output)
    assert isinstance(data, dict)


def test_json_error_contains_error_key() -> None:
    result = assert_invoke(
        app, ["--json-output", "add", "s99", "Task"], expect_error=True
    )
    data = _parse_json(result.output)
    assert "error" in data


def test_json_error_message_is_non_empty() -> None:
    result = assert_invoke(
        app, ["--json-output", "add", "s99", "Task"], expect_error=True
    )
    data = _parse_json(result.output)
    assert data["error"]


def test_json_error_exits_nonzero() -> None:
    result = assert_invoke(
        app, ["--json-output", "add", "s99", "Task"], expect_error=True
    )
    assert result.exit_code != 0


def test_json_error_no_plain_error_prefix() -> None:
    result = assert_invoke(
        app, ["--json-output", "add", "s99", "Task"], expect_error=True
    )
    assert "Error:" not in result.output


# --- debug + json ---


def test_json_debug_error_includes_traceback() -> None:
    result = assert_invoke(
        app, ["--json-output", "--debug", "add", "s99", "Task"], expect_error=True
    )
    data = _parse_json(result.output)
    assert "traceback" in data


def test_json_debug_error_traceback_non_empty() -> None:
    result = assert_invoke(
        app, ["--json-output", "--debug", "add", "s99", "Task"], expect_error=True
    )
    data = _parse_json(result.output)
    assert data["traceback"]


def test_json_no_debug_error_no_traceback() -> None:
    result = assert_invoke(
        app, ["--json-output", "add", "s99", "Task"], expect_error=True
    )
    data = _parse_json(result.output)
    assert "traceback" not in data


# --- task_ref in errors ---


def test_json_error_contains_task_ref() -> None:
    result = assert_invoke(
        app, ["--json-output", "add", "s99", "Task"], expect_error=True
    )
    data = _parse_json(result.output)
    assert "task_ref" in data


def test_json_error_task_ref_is_non_empty() -> None:
    result = assert_invoke(
        app, ["--json-output", "add", "s99", "Task"], expect_error=True
    )
    data = _parse_json(result.output)
    assert data["task_ref"]


def test_json_error_task_ref_contains_task_id() -> None:
    result = assert_invoke(
        app, ["--json-output", "add", "s99", "Task"], expect_error=True
    )
    data = _parse_json(result.output)
    assert "s99" in data["task_ref"]


# --- start command ---


def test_json_start_outputs_task_ref() -> None:
    assert_invoke(app, ["new", "My story"])
    assert_invoke(app, ["add", "s01", "Leaf task"])
    result = assert_invoke(app, ["--json-output", "start", "s01t01"])
    data = _parse_json(result.output)
    assert data["task_refs"] == ["s01t01"]


def test_json_start_nonleaf_outputs_error() -> None:
    assert_invoke(app, ["new", "My story"])
    assert_invoke(app, ["add", "s01", "Leaf task"])
    result = assert_invoke(app, ["--json-output", "start", "s01"], expect_error=True)
    data = _parse_json(result.output)
    assert "error" in data


def test_json_start_nonexistent_outputs_error() -> None:
    result = assert_invoke(app, ["--json-output", "start", "s99t01"], expect_error=True)
    data = _parse_json(result.output)
    assert "error" in data


# --- done command ---


def test_json_done_outputs_task_ref() -> None:
    assert_invoke(app, ["new", "My story"])
    assert_invoke(app, ["add", "s01", "Leaf task"])
    result = assert_invoke(app, ["--json-output", "done", "s01t01"])
    data = _parse_json(result.output)
    assert data["task_refs"] == ["s01t01"]


def test_json_done_nonleaf_outputs_error() -> None:
    assert_invoke(app, ["new", "My story"])
    assert_invoke(app, ["add", "s01", "Leaf task"])
    result = assert_invoke(app, ["--json-output", "done", "s01"], expect_error=True)
    data = _parse_json(result.output)
    assert "error" in data


def test_json_done_force_outputs_task_ref() -> None:
    assert_invoke(app, ["new", "My story"])
    assert_invoke(app, ["add", "s01", "Subtask one"])
    assert_invoke(app, ["add", "s01", "Subtask two"])
    result = assert_invoke(app, ["--json-output", "done", "--force", "s01"])
    data = _parse_json(result.output)
    assert data["task_refs"] == ["s01-my-story"]


def test_json_done_force_includes_forced_task_ids() -> None:
    assert_invoke(app, ["new", "My story"])
    assert_invoke(app, ["add", "s01", "Subtask one"])
    assert_invoke(app, ["add", "s01", "Subtask two"])
    result = assert_invoke(app, ["--json-output", "done", "--force", "s01"])
    data = _parse_json(result.output)
    assert set(data["forced_task_ids"]) == {"s01t01", "s01t02"}


def test_json_done_force_no_forced_when_all_done() -> None:
    assert_invoke(app, ["new", "My story"])
    assert_invoke(app, ["add", "s01", "Subtask one"])
    assert_invoke(app, ["done", "s01t01"])
    result = assert_invoke(app, ["--json-output", "done", "--force", "s01"])
    data = _parse_json(result.output)
    assert data.get("forced_task_ids") is None


def test_json_done_nonexistent_outputs_error() -> None:
    result = assert_invoke(app, ["--json-output", "done", "s99t01"], expect_error=True)
    data = _parse_json(result.output)
    assert "error" in data
