import json

from tasker.cli import app

from .helpers import add_subtask, assert_invoke, create_task


def test_show_task_prints_title() -> None:
    task_id = create_task("My important story").task_id
    result = assert_invoke(app, ["show", task_id])
    assert "My important story" in result.output


def test_show_task_omits_pending_marker() -> None:
    task_id = create_task("My story").task_id
    result = assert_invoke(app, ["show", task_id])
    assert "[ ]" not in result.output


def test_show_task_prints_task_id_in_header() -> None:
    task_id = create_task("My story").task_id
    result = assert_invoke(app, ["show", task_id])
    assert task_id in result.output


def test_show_task_prints_description() -> None:
    task_id = create_task("My story").task_id
    assert_invoke(app, ["edit", task_id, "--details", "Some description here"])
    result = assert_invoke(app, ["show", task_id])
    assert "Some description here" in result.output


def test_show_task_no_description_section_when_empty() -> None:
    task_id = create_task("My story").task_id
    result = assert_invoke(app, ["show", task_id])
    assert "None" not in result.output


def test_show_task_prints_subtasks() -> None:
    task_id = create_task("My story").task_id
    sub_id = add_subtask(task_id, "First subtask").task_id
    result = assert_invoke(app, ["show", task_id])
    assert sub_id in result.output
    assert "First subtask" in result.output


def test_show_task_prints_subtask_status_marker() -> None:
    task_id = create_task("My story").task_id
    sub_id = add_subtask(task_id, "First subtask").task_id
    assert_invoke(app, ["start", sub_id])
    result = assert_invoke(app, ["show", task_id])
    assert "[~]" in result.output


def test_show_task_saves_recent() -> None:
    task_id = create_task("My story").task_id
    assert_invoke(app, ["show", task_id])
    result = assert_invoke(app, ["show", "q"])
    assert "My story" in result.output


def test_show_task_json_output_fields() -> None:
    task_id = create_task("My story").task_id
    assert_invoke(app, ["edit", task_id, "--details", "Some details"])
    result = assert_invoke(app, ["--json-output", "show", task_id])
    data = json.loads(result.output)
    assert data["id"] == task_id
    assert data["title"] == "My story"
    assert data["status"] == "pending"
    assert data["description"] == "Some details"
    assert data["subtasks"] == []


def test_show_task_json_output_subtasks() -> None:
    task_id = create_task("My story").task_id
    sub_id = add_subtask(task_id, "First subtask").task_id
    result = assert_invoke(app, ["--json-output", "show", task_id])
    data = json.loads(result.output)
    assert len(data["subtasks"]) == 1
    assert data["subtasks"][0]["id"] == sub_id
    assert data["subtasks"][0]["title"] == "First subtask"
    assert data["subtasks"][0]["status"] == "pending"


def test_show_task_json_output_no_description_is_null() -> None:
    task_id = create_task("My story").task_id
    result = assert_invoke(app, ["--json-output", "show", task_id])
    data = json.loads(result.output)
    assert data["description"] is None
