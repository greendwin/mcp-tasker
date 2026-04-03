import json

from tasker.cli import app

from .helpers import add_subtask, assert_invoke, create_task


def test_list_shows_task_title() -> None:
    task_id = create_task("My story").task_id
    result = assert_invoke(app, ["list"])
    assert task_id in result.output
    assert "My story" in result.output


def test_list_no_tasks_prints_empty_message() -> None:
    result = assert_invoke(app, ["list"])
    assert "No tasks to show" in result.output


def test_list_shows_open_subtask() -> None:
    task_id = create_task("My story").task_id
    sub_id = add_subtask(task_id, "First subtask").task_id
    result = assert_invoke(app, ["list"])
    assert sub_id in result.output
    assert "First subtask" in result.output


def test_list_hides_done_subtask_by_default() -> None:
    task_id = create_task("My story").task_id
    sub_id = add_subtask(task_id, "Done subtask").task_id
    assert_invoke(app, ["done", sub_id])
    result = assert_invoke(app, ["list"])
    assert sub_id not in result.output


def test_list_hides_cancelled_subtask_by_default() -> None:
    task_id = create_task("My story").task_id
    sub_id = add_subtask(task_id, "Cancelled subtask").task_id
    assert_invoke(app, ["cancel", sub_id])
    result = assert_invoke(app, ["list"])
    assert sub_id not in result.output


def test_list_closed_json_output() -> None:
    task_id = create_task("My story").task_id
    sub_id = add_subtask(task_id, "Done subtask").task_id
    assert_invoke(app, ["done", sub_id])
    result = assert_invoke(app, ["--json-output", "list"])
    data = json.loads(result.output)
    # Without --closed, JSON subtasks only show open ones... but _task_to_json
    # includes all subtasks. This is existing behavior.
    task_data = data["tasks"][0]
    assert task_data["id"] == task_id


# --all shows full depth and closed


def test_list_all_shows_nested_subtask() -> None:
    task_id = create_task("My story").task_id
    sub_id = add_subtask(task_id, "Sub", details="desc").task_id
    nested_id = add_subtask(sub_id, "Nested subtask").task_id
    result = assert_invoke(app, ["list", "--all"])
    assert nested_id in result.output
    assert "Nested subtask" in result.output


def test_list_shows_nested_subtask_by_default() -> None:
    task_id = create_task("My story").task_id
    sub_id = add_subtask(task_id, "Sub", details="desc").task_id
    nested_id = add_subtask(sub_id, "Nested subtask").task_id
    result = assert_invoke(app, ["list"])
    assert nested_id in result.output


def test_list_all_shows_closed_subtask() -> None:
    task_id = create_task("My story").task_id
    sub_id = add_subtask(task_id, "Done subtask").task_id
    assert_invoke(app, ["done", sub_id])
    result = assert_invoke(app, ["list", "--all"])
    assert sub_id in result.output


def test_list_all_shows_closed_nested_subtask() -> None:
    task_id = create_task("My story").task_id
    sub_id = add_subtask(task_id, "Sub", details="desc").task_id
    nested_id = add_subtask(sub_id, "Nested done").task_id
    assert_invoke(app, ["done", nested_id])
    result = assert_invoke(app, ["list", "--all"])
    assert nested_id in result.output


# cancelled subtasks shown full gray (no blue ID)


def test_list_all_cancelled_subtask_has_no_blue_id() -> None:
    task_id = create_task("My story").task_id
    sub_id = add_subtask(task_id, "Cancelled subtask").task_id
    assert_invoke(app, ["cancel", sub_id])
    result = assert_invoke(app, ["list", "--all"])
    # cancelled line should not linkify the ID in blue
    assert f"[blue]{sub_id}[/blue]" not in result.output
    assert sub_id in result.output


def test_list_default_no_cancelled_subtask_in_output() -> None:
    task_id = create_task("My story").task_id
    sub_id = add_subtask(task_id, "Cancelled subtask").task_id
    assert_invoke(app, ["cancel", sub_id])
    result = assert_invoke(app, ["list"])
    assert sub_id not in result.output


# --all always shows status marker (even for pending)


def test_list_all_shows_pending_marker() -> None:
    task_id = create_task("My story").task_id
    add_subtask(task_id, "Pending subtask").task_id
    result = assert_invoke(app, ["list", "--all"])
    assert "[ ]" in result.output


def test_list_default_no_pending_marker_for_subtask() -> None:
    task_id = create_task("My story").task_id
    add_subtask(task_id, "Pending subtask").task_id
    result = assert_invoke(app, ["list"])
    assert "[ ]" not in result.output


# accept args to filter subtrees


def test_list_args_shows_only_specified_task() -> None:
    task1_id = create_task("First story").task_id
    task2_id = create_task("Second story").task_id
    result = assert_invoke(app, ["list", task1_id])
    assert task1_id in result.output
    assert task2_id not in result.output


def test_list_args_shows_subtasks_of_specified_task() -> None:
    task_id = create_task("My story").task_id
    sub_id = add_subtask(task_id, "My subtask").task_id
    result = assert_invoke(app, ["list", task_id])
    assert sub_id in result.output


def test_list_args_multiple_tasks() -> None:
    task1_id = create_task("First story").task_id
    task2_id = create_task("Second story").task_id
    task3_id = create_task("Third story").task_id
    result = assert_invoke(app, ["list", task1_id, task3_id])
    assert task1_id in result.output
    assert task2_id not in result.output
    assert task3_id in result.output


# --- --archived lists archived tasks ---


def test_list_archived_shows_archived_task() -> None:
    task_id = create_task("My story").task_id
    assert_invoke(app, ["done", "--force", task_id])
    assert_invoke(app, ["archive", task_id])
    result = assert_invoke(app, ["list", "--archived"])
    assert task_id in result.output
    assert "My story" in result.output


def test_list_archived_hides_active_tasks() -> None:
    active_id = create_task("Active story").task_id
    archived_id = create_task("Archived story").task_id
    assert_invoke(app, ["done", "--force", archived_id])
    assert_invoke(app, ["archive", archived_id])
    result = assert_invoke(app, ["list", "--archived"])
    assert archived_id in result.output
    assert active_id not in result.output


def test_list_archived_empty() -> None:
    create_task("My story")
    result = assert_invoke(app, ["list", "--archived"])
    assert "No tasks to show" in result.output


def test_list_archived_json_output() -> None:
    task_id = create_task("My story").task_id
    assert_invoke(app, ["done", "--force", task_id])
    assert_invoke(app, ["archive", task_id])
    result = assert_invoke(app, ["--json-output", "list", "--archived"])
    data = json.loads(result.output)
    assert len(data["tasks"]) == 1
    assert data["tasks"][0]["id"] == task_id


def test_list_archived_shows_subtasks() -> None:
    task_id = create_task("My story").task_id
    sub_id = add_subtask(task_id, "My subtask").task_id
    assert_invoke(app, ["done", "--force", task_id])
    assert_invoke(app, ["archive", task_id])
    result = assert_invoke(app, ["list", "--archived", "--all"])
    assert sub_id in result.output


def test_list_all_indents_nested_subtasks() -> None:
    task_id = create_task("My story").task_id
    sub_id = add_subtask(task_id, "Sub", details="desc").task_id
    nested_id = add_subtask(sub_id, "Nested subtask").task_id
    result = assert_invoke(app, ["list", "--all"])
    # nested subtask line should have deeper indentation than direct subtask
    lines = result.output.splitlines()
    sub_line = next(ln for ln in lines if sub_id in ln)
    nested_line = next(ln for ln in lines if nested_id in ln)
    sub_indent = len(sub_line) - len(sub_line.lstrip())
    nested_indent = len(nested_line) - len(nested_line.lstrip())
    assert nested_indent > sub_indent
