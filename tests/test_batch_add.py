import json

import pytest

from tasker.base_types import TaskStatus
from tasker.cli import app
from tasker.parse import parse_task_file

from .helpers import GetTaskFile, add_subtask, assert_invoke, create_task


@pytest.fixture()
def parent_id() -> str:
    return create_task("Batch story").task_id


# --- basic creation ---


def test_batch_creates_single_task(parent_id: str, get_task_file: GetTaskFile) -> None:
    assert_invoke(app, ["add-many", parent_id], input="First task\n\n")
    assert f"- [ ] {parent_id}t01: First task" in get_task_file(parent_id).read_text()


def test_batch_creates_multiple_tasks(
    parent_id: str, get_task_file: GetTaskFile
) -> None:
    assert_invoke(app, ["add-many", parent_id], input="Task one\nTask two\n\n")
    content = get_task_file(parent_id).read_text()
    assert f"- [ ] {parent_id}t01: Task one" in content
    assert f"- [ ] {parent_id}t02: Task two" in content


def test_batch_titles_are_capitalized(
    parent_id: str, get_task_file: GetTaskFile
) -> None:
    assert_invoke(app, ["add-many", parent_id], input="lowercase title\n\n")
    assert "Lowercase title" in get_task_file(parent_id).read_text()


# --- stopping conditions ---


def test_batch_stops_on_empty_line(parent_id: str, get_task_file: GetTaskFile) -> None:
    assert_invoke(app, ["add-many", parent_id], input="First\n\nIgnored\n")
    content = get_task_file(parent_id).read_text()
    assert f"{parent_id}t01" in content
    assert "Ignored" not in content


def test_batch_stops_on_eof(parent_id: str, get_task_file: GetTaskFile) -> None:
    assert_invoke(app, ["add-many", parent_id], input="First\nSecond")
    content = get_task_file(parent_id).read_text()
    assert f"{parent_id}t01" in content
    assert f"{parent_id}t02" in content


# --- normal-mode output ---


def test_batch_output_mentions_all_ids(parent_id: str) -> None:
    result = assert_invoke(app, ["add-many", parent_id], input="Alpha\nBeta\n\n")
    assert f"{parent_id}t01" in result.output
    assert f"{parent_id}t02" in result.output


def test_batch_shows_prompt(parent_id: str) -> None:
    result = assert_invoke(app, ["add-many", parent_id], input="Task\n\n")
    assert ">" in result.output


def test_batch_empty_input_shows_no_tasks_added(parent_id: str) -> None:
    result = assert_invoke(app, ["add-many", parent_id], input="\n")
    assert "No tasks added" in result.output


# --- JSON output mode ---


def test_batch_json_outputs_parent_ref(parent_id: str) -> None:
    result = assert_invoke(
        app, ["--json-output", "add-many", parent_id], input="A\nB\n\n"
    )
    data = json.loads(result.output.strip())
    assert "parent_ref" in data
    assert data["parent_ref"] == parent_id


def test_batch_json_task_ids(parent_id: str) -> None:
    result = assert_invoke(
        app, ["--json-output", "add-many", parent_id], input="A\nB\n\n"
    )
    data = json.loads(result.output.strip())
    assert "task_refs" in data
    assert isinstance(data["task_refs"], list)
    assert data["task_refs"] == [f"{parent_id}t01", f"{parent_id}t02"]


def test_batch_json_output_is_only_json(parent_id: str) -> None:
    result = assert_invoke(
        app, ["--json-output", "add-many", parent_id], input="Task\n\n"
    )
    json.loads(result.output.strip())  # must not raise


def test_batch_json_no_prompt_in_output(parent_id: str) -> None:
    result = assert_invoke(
        app, ["--json-output", "add-many", parent_id], input="Task\n\n"
    )
    assert ">" not in result.output


def test_batch_json_empty_input_returns_empty_list(parent_id: str) -> None:
    result = assert_invoke(app, ["--json-output", "add-many", parent_id], input="\n")
    data = json.loads(result.output.strip())
    assert data["task_refs"] == []


# --- adding subtasks updates parent status ---


def test_batch_add_to_done_parent_reopens_it(
    parent_id: str, get_task_file: GetTaskFile
) -> None:
    t01 = add_subtask(parent_id, "First subtask").task_id
    assert_invoke(app, ["done", t01])
    # parent is now done; batch-adding should reopen it
    assert_invoke(app, ["add-many", parent_id], input="New task\n\n")
    task = parse_task_file(get_task_file(parent_id)).task
    assert task.status == TaskStatus.PENDING
