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
    data = json.loads(result.output)["task"]
    assert data["id"] == task_id
    assert data["title"] == "My story"
    assert data["status"] == "pending"
    assert data["description"] == "Some details"
    assert data["subtasks"] == []


def test_show_task_json_output_subtasks() -> None:
    task_id = create_task("My story").task_id
    sub_id = add_subtask(task_id, "First subtask").task_id
    result = assert_invoke(app, ["--json-output", "show", task_id])
    data = json.loads(result.output)["task"]
    assert len(data["subtasks"]) == 1
    assert data["subtasks"][0]["id"] == sub_id
    assert data["subtasks"][0]["title"] == "First subtask"
    assert data["subtasks"][0]["status"] == "pending"


def test_show_task_json_output_no_description_is_null() -> None:
    task_id = create_task("My story").task_id
    result = assert_invoke(app, ["--json-output", "show", task_id])
    data = json.loads(result.output)["task"]
    assert data["description"] is None


def test_show_task_subtask_count_not_shown_when_no_subtasks() -> None:
    task_id = create_task("My story").task_id
    add_subtask(task_id, "Leaf subtask")
    result = assert_invoke(app, ["show", task_id])
    assert "subtasks)" not in result.output


def test_show_task_subtask_count_shown_when_has_subtasks() -> None:
    task_id = create_task("My story").task_id
    sub_id = add_subtask(task_id, "Parent subtask").task_id
    add_subtask(sub_id, "Nested child", details="child details")
    result = assert_invoke(app, ["show", task_id])
    assert "(+1 subtasks)" in result.output


def test_show_task_subtask_count_recursive() -> None:
    task_id = create_task("My story").task_id
    sub_id = add_subtask(task_id, "Parent subtask").task_id
    child_id = add_subtask(sub_id, "Child", details="d1").task_id
    add_subtask(child_id, "Grandchild", details="d2")
    result = assert_invoke(app, ["show", task_id])
    assert "(+2 subtasks)" in result.output


# recent markers in view


def test_show_task_marks_recent_task() -> None:
    task_id = create_task("My story").task_id
    assert_invoke(app, ["start", task_id])
    result = assert_invoke(app, ["show", task_id])
    line = result.output.splitlines()[0]
    assert "(q)" in line


def test_show_task_marks_recent_subtask() -> None:
    task_id = create_task("My story").task_id
    sub_id = add_subtask(task_id, "My subtask").task_id
    assert_invoke(app, ["start", sub_id])

    # note: use relative ref to avoid resetting 'recent'
    result = assert_invoke(app, ["show", "p"])
    sub_line = next(ln for ln in result.output.splitlines() if sub_id in ln)
    assert "(q)" in sub_line

    # in case of direct ref recent will b set to story
    result = assert_invoke(app, ["show", task_id])
    assert "(q)" in result.output.splitlines()[0]


def test_show_task_p_marker_when_recent_is_nested() -> None:
    task_id = create_task("My story").task_id
    sub_id = add_subtask(task_id, "Parent sub", details="d").task_id
    nested_id = add_subtask(sub_id, "Nested").task_id
    assert_invoke(app, ["start", nested_id])

    # use relativ link, otherwise recent will be reset
    result = assert_invoke(app, ["show", "pp"])
    # nested_id is not a direct subtask, so sub_id should show (p)
    sub_line = next(ln for ln in result.output.splitlines() if sub_id in ln)
    assert "(p)" in sub_line


def test_show_task_no_marker_on_unrelated_subtask() -> None:
    task_id = create_task("My story").task_id
    sub1_id = add_subtask(task_id, "First subtask").task_id
    sub2_id = add_subtask(task_id, "Second subtask").task_id
    assert_invoke(app, ["start", sub1_id])
    result = assert_invoke(app, ["show", task_id])
    sub2_line = next(ln for ln in result.output.splitlines() if sub2_id in ln)
    assert "(q)" not in sub2_line
    assert "(p)" not in sub2_line
