import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence
from unittest import mock

import pytest
from typer import Typer
from typer.testing import CliRunner

from tasker.cli import _helpers, app
from tasker.parse import ParsedRef, parse_task_ref

_runner = CliRunner()


@dataclass
class Result:
    exit_code: int
    output: str


def assert_invoke(
    app: Typer,
    args: Sequence[str],
    *,
    expect_error: bool = False,
    input: str | None = None,
) -> Result:
    raw = _runner.invoke(app, list(args), input=input, catch_exceptions=False)
    result = Result(exit_code=raw.exit_code, output=raw.output)
    if expect_error:
        if result.exit_code == 0:
            raise AssertionError(
                f"Command was expected to fail but exited with code 0:\n{result.output}"
            )
    elif result.exit_code != 0:
        raise AssertionError(
            f"Command exited with code {result.exit_code}:\n{result.output}"
        )
    return result


def create_task(title: str) -> ParsedRef:
    result = assert_invoke(app, ["--json-output", "new", title])
    task_ref = json.loads(result.output.strip())["task_ref"]
    return parse_task_ref(task_ref)


def add_subtask(parent_ref: str, title: str, details: str | None = None) -> ParsedRef:
    args = ["--json-output", "add", parent_ref, title]
    if details is not None:
        args.extend(["--details", details])

    result = assert_invoke(app, args)
    task_ref = json.loads(result.output.strip())["task_ref"]
    return parse_task_ref(task_ref)


class GetTaskFile(Protocol):
    def __call__(self, task_id: str) -> Path: ...


@pytest.fixture
def get_task_file(tasks_root: Path) -> GetTaskFile:
    def callback(task_id: str) -> Path:
        path = next(tasks_root.glob(f"{task_id}-*.md"), None)
        assert path is not None, f"No task file found for {task_id!r} in {tasks_root}"
        return path

    return callback


@pytest.fixture(autouse=True)
def run_editor(monkeypatch: pytest.MonkeyPatch) -> mock.Mock:
    # always mock `open_in_editor` to avoid process spawn
    m = mock.Mock(return_value=None)
    monkeypatch.setattr(_helpers, "run_editor", m)
    return m


class SetupTaskEdits(Protocol):
    def __call__(self, *args: tuple[str, str]) -> list[str]:
        """returns original contents before edits"""
        ...


@pytest.fixture
def setup_task_edits(run_editor: mock.Mock) -> SetupTaskEdits:
    def callback(*args: tuple[str, str]) -> list[str]:
        orig_content: list[str] = []

        def fake_edit(path: Path) -> None:
            content = path.read_text()
            orig_content.append(content)
            for old, new in args:
                content = content.replace(old, new)
            path.write_text(content)

        run_editor.reset_mock()
        run_editor.side_effect = fake_edit

        return orig_content

    return callback
