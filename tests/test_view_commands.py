"""Tests for view commands: show and list."""

import json

from tasker.cli import app

from .helpers import add_subtask, assert_invoke, create_task

# ---------------------------------------------------------------------------
# show command (from test_show_task.py)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# list command (from test_list_tasks.py)
# ---------------------------------------------------------------------------


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

    # close another task to clear the recently-closed list
    task2_id = create_task("Other story").task_id
    sub2_id = add_subtask(task2_id, "Another subtask").task_id
    assert_invoke(app, ["done", sub2_id])

    result = assert_invoke(app, ["list"])
    assert sub_id not in result.output


def test_list_hides_cancelled_subtask_by_default() -> None:
    task_id = create_task("My story").task_id
    sub_id = add_subtask(task_id, "Cancelled subtask").task_id
    assert_invoke(app, ["cancel", sub_id])

    # close another task to clear the recently-closed list
    task2_id = create_task("Other story").task_id
    sub2_id = add_subtask(task2_id, "Another subtask").task_id
    assert_invoke(app, ["done", sub2_id])

    result = assert_invoke(app, ["list"])
    assert sub_id not in result.output


def test_list_closed_json_output() -> None:
    task_id = create_task("My story").task_id
    sub_id = add_subtask(task_id, "Done subtask").task_id
    assert_invoke(app, ["done", sub_id])
    result = assert_invoke(app, ["--json-output", "list"])
    data = json.loads(result.output)
    task_data = data["tasks"][0]
    assert task_data["id"] == task_id


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


def test_list_all_cancelled_subtask_has_no_blue_id() -> None:
    task_id = create_task("My story").task_id
    sub_id = add_subtask(task_id, "Cancelled subtask").task_id
    assert_invoke(app, ["cancel", sub_id])
    result = assert_invoke(app, ["list", "--all"])
    assert "[blue]" not in next(ln for ln in result.output.splitlines() if sub_id in ln)
    assert sub_id in result.output


def test_list_default_no_cancelled_subtask_in_output() -> None:
    task_id = create_task("My story").task_id
    sub_id = add_subtask(task_id, "Cancelled subtask").task_id
    assert_invoke(app, ["cancel", sub_id])

    # close another task to clear the recently-closed list
    task2_id = create_task("Other story").task_id
    sub2_id = add_subtask(task2_id, "Another subtask").task_id
    assert_invoke(app, ["done", sub2_id])

    result = assert_invoke(app, ["list"])
    assert sub_id not in result.output


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
    lines = result.output.splitlines()
    sub_line = next(ln for ln in lines if sub_id in ln)
    nested_line = next(ln for ln in lines if nested_id in ln)
    sub_indent = len(sub_line) - len(sub_line.lstrip())
    nested_indent = len(nested_line) - len(nested_line.lstrip())
    assert nested_indent > sub_indent


def test_list_marks_recent_root_task() -> None:
    task_id = create_task("My story").task_id
    assert_invoke(app, ["start", task_id])  # saves recent
    result = assert_invoke(app, ["list"])
    line = next(ln for ln in result.output.splitlines() if task_id in ln)
    assert "q" in line


def test_list_marks_recent_subtask() -> None:
    task_id = create_task("My story").task_id
    sub_id = add_subtask(task_id, "My subtask").task_id
    assert_invoke(app, ["start", sub_id])  # saves recent
    result = assert_invoke(app, ["list"])
    line = next(ln for ln in result.output.splitlines() if sub_id in ln)
    assert "q" in line


def test_list_recent_marker_only_on_accessed_task() -> None:
    task1_id = create_task("First story").task_id
    task2_id = create_task("Second story").task_id
    assert_invoke(app, ["start", task1_id])  # saves task1 as recent
    result = assert_invoke(app, ["list"])
    lines = result.output.splitlines()
    task1_line = next(ln for ln in lines if task1_id in ln)
    task2_line = next(ln for ln in lines if task2_id in ln)
    assert "q" in task1_line
    assert "q" not in task2_line


def test_list_shows_recently_closed_subtask_with_q_marker() -> None:
    task_id = create_task("My story").task_id
    sub_id = add_subtask(task_id, "Done subtask").task_id
    assert_invoke(app, ["start", sub_id])
    assert_invoke(app, ["done", sub_id])  # recent = sub_id, recently closed
    result = assert_invoke(app, ["list"])
    sub_line = next(ln for ln in result.output.splitlines() if sub_id in ln)
    assert "(q)" in sub_line


def test_list_shows_pp_marker_when_recent_is_two_levels_deep() -> None:
    task_id = create_task("My story").task_id
    sub_id = add_subtask(task_id, "Middle task", details="d").task_id
    nested_id = add_subtask(sub_id, "Nested task").task_id
    assert_invoke(app, ["done", "--force", sub_id])  # closes sub + nested
    assert_invoke(app, ["start", nested_id])  # recent = nested_id

    # close a different task so nested_id is no longer recently closed
    other_id = create_task("Other").task_id
    other_sub = add_subtask(other_id, "Other sub").task_id
    assert_invoke(app, ["done", other_sub])

    # set recent back to nested_id (via start) then close it
    assert_invoke(app, ["done", nested_id])  # recent = nested_id, closed again

    # nested_id is recently closed, so it should be visible with (q) marker
    result = assert_invoke(app, ["list"])
    nested_line = next(ln for ln in result.output.splitlines() if nested_id in ln)
    assert "(q)" in nested_line


def test_list_shows_recently_closed_nested_with_q_marker() -> None:
    task_id = create_task("My story").task_id
    sub_id = add_subtask(task_id, "Open parent", details="d").task_id
    nested_id = add_subtask(sub_id, "Done child").task_id
    add_subtask(sub_id, "Still open")  # keep sub_id open after done
    assert_invoke(app, ["start", nested_id])
    assert_invoke(app, ["done", nested_id])  # nested closed, recently closed
    result = assert_invoke(app, ["list"])
    lines = result.output.splitlines()
    nested_line = next(ln for ln in lines if nested_id in ln)
    assert "(q)" in nested_line


def test_list_no_p_marker_with_show_all() -> None:
    task_id = create_task("My story").task_id
    sub_id = add_subtask(task_id, "Done subtask").task_id
    assert_invoke(app, ["start", sub_id])
    assert_invoke(app, ["done", sub_id])
    result = assert_invoke(app, ["list", "--all"])
    sub_line = next(ln for ln in result.output.splitlines() if sub_id in ln)
    assert "(q)" in sub_line
    task_line = next(ln for ln in result.output.splitlines() if task_id in ln)
    assert "(p)" not in task_line


def test_list_recently_cancelled_subtask_visible_with_q_marker() -> None:
    task_id = create_task("My story").task_id
    sub_id = add_subtask(task_id, "Cancelled subtask").task_id
    assert_invoke(app, ["start", sub_id])
    assert_invoke(app, ["cancel", sub_id])  # recent = sub_id, recently closed
    result = assert_invoke(app, ["list"])
    sub_line = next(ln for ln in result.output.splitlines() if sub_id in ln)
    assert "(q)" in sub_line


def test_list_shows_recently_done_subtask() -> None:
    task_id = create_task("My story").task_id
    sub_id = add_subtask(task_id, "Finished subtask").task_id
    assert_invoke(app, ["done", sub_id])
    result = assert_invoke(app, ["list"])
    assert sub_id in result.output


def test_list_shows_recently_cancelled_subtask() -> None:
    task_id = create_task("My story").task_id
    sub_id = add_subtask(task_id, "Cancelled subtask").task_id
    assert_invoke(app, ["cancel", sub_id])
    result = assert_invoke(app, ["list"])
    assert sub_id in result.output


def test_list_recently_closed_replaced_by_next_done() -> None:
    task_id = create_task("My story").task_id
    sub1 = add_subtask(task_id, "First subtask").task_id
    sub2 = add_subtask(task_id, "Second subtask").task_id
    assert_invoke(app, ["done", sub1])
    assert_invoke(app, ["done", sub2])
    result = assert_invoke(app, ["list"])
    # only the most recently closed (sub2) should show
    assert sub1 not in result.output
    assert sub2 in result.output


def test_list_recently_closed_force_shows_all_forced() -> None:
    task_id = create_task("My story").task_id
    sub1 = add_subtask(task_id, "Subtask A").task_id
    sub2 = add_subtask(task_id, "Subtask B").task_id
    assert_invoke(app, ["done", "--force", task_id])
    result = assert_invoke(app, ["list"])
    assert task_id in result.output
    assert sub1 in result.output
    assert sub2 in result.output


def test_list_recently_closed_shows_parent_chain() -> None:
    task_id = create_task("My story").task_id
    sub_id = add_subtask(task_id, "Middle", details="d").task_id
    nested_id = add_subtask(sub_id, "Nested").task_id
    # close all other subtasks so parent would normally be hidden
    assert_invoke(app, ["done", "--force", task_id])

    # close another task to make only nested_id recently closed
    task2_id = create_task("Other").task_id
    other_sub = add_subtask(task2_id, "Other sub").task_id
    assert_invoke(app, ["done", other_sub])

    # now reopen nested_id and close it again
    assert_invoke(app, ["reset", nested_id])
    assert_invoke(app, ["done", nested_id])
    result = assert_invoke(app, ["list"])
    # nested_id should be visible, along with its parent chain
    assert nested_id in result.output
    assert sub_id in result.output


def test_list_after_deleting_recent_task_does_not_crash() -> None:
    task_id = create_task("My story").task_id
    sub_id = add_subtask(task_id, "Subtask").task_id
    assert_invoke(app, ["start", sub_id])  # saves recent
    assert_invoke(app, ["move", sub_id, "--delete"])
    result = assert_invoke(app, ["list"])
    assert task_id in result.output


def test_list_archived_hides_recently_closed_non_archived_tasks() -> None:
    task_id = create_task("My story").task_id
    sub_id = add_subtask(task_id, "Subtask").task_id
    assert_invoke(app, ["done", sub_id])  # recently closed, non-archived

    archived_id = create_task("Archived story").task_id
    assert_invoke(app, ["done", "--force", archived_id])
    assert_invoke(app, ["archive", archived_id])

    result = assert_invoke(app, ["list", "--archived"])
    assert archived_id in result.output
    assert sub_id not in result.output  # should not show non-archived closed tasks


def test_list_archived_with_explicit_task_refs_shows_those_tasks() -> None:
    task_id = create_task("My story").task_id
    sub_id = add_subtask(task_id, "Subtask").task_id
    assert_invoke(app, ["done", sub_id])

    archived_id = create_task("Archived story").task_id
    assert_invoke(app, ["done", "--force", archived_id])
    assert_invoke(app, ["archive", archived_id])

    result = assert_invoke(app, ["list", "--archived", task_id])
    assert archived_id in result.output
    assert task_id in result.output  # explicit task_ref should be shown


def test_list_with_task_ref_hides_recently_closed_other_tasks() -> None:
    task1_id = create_task("First story").task_id
    task2_id = create_task("Second story").task_id
    sub2_id = add_subtask(task2_id, "Subtask of second").task_id
    assert_invoke(app, ["done", sub2_id])  # recently closed, but in task2

    result = assert_invoke(app, ["list", task1_id])
    assert task1_id in result.output
    assert (
        sub2_id not in result.output
    )  # should not show recently-closed from other task


def test_list_with_todo_hides_recently_closed() -> None:
    task_id = create_task("My story").task_id
    sub_id = add_subtask(task_id, "Subtask").task_id
    assert_invoke(app, ["done", sub_id])  # recently closed

    assert_invoke(app, ["todo", task_id])

    result = assert_invoke(app, ["list", "--todo"])
    assert task_id in result.output
    assert (
        sub_id not in result.output
    )  # should not show recently-closed when using --todo


def test_list_with_all_hides_recently_closed_outside_tree() -> None:
    task1_id = create_task("First story").task_id
    task2_id = create_task("Second story").task_id
    sub2_id = add_subtask(task2_id, "Subtask of second").task_id
    assert_invoke(app, ["done", sub2_id])  # recently closed

    result = assert_invoke(app, ["list", "--all", task1_id])
    assert task1_id in result.output
    assert (
        sub2_id not in result.output
    )  # should not add recently-closed outside the specified tree


def test_add_command_hides_recently_closed_in_parent_preview() -> None:
    task1_id = create_task("Parent task").task_id
    task2_id = create_task("Other task").task_id
    sub2_id = add_subtask(task2_id, "Recently closed sub").task_id
    assert_invoke(app, ["done", sub2_id])  # recently closed

    result = assert_invoke(app, ["add", task1_id, "New subtask"])
    # Should not show recently-closed tasks from other trees in parent preview
    assert task1_id in result.output
    assert "New subtask" in result.output
    assert sub2_id not in result.output
