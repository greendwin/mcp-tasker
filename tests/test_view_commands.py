"""Tests for view commands: show and list."""

import json
from pathlib import Path

from tasker.cli import app, get_task_repo
from tasker.todo import load_todo_ids, save_todo_ids

from .helpers import GetTaskFile, add_subtask, assert_invoke, create_task

# ---------------------------------------------------------------------------
# show command (from test_show_task.py)
# ---------------------------------------------------------------------------


def test_show_task_prints_title() -> None:
    task_id = create_task("My important story").task_id
    result = assert_invoke(app, ["show", task_id])
    assert "My important story" in result.output


def test_show_task_prints_title_with_brackets_literally() -> None:
    task_id = create_task("Story [red]urgent[/red] case").task_id
    result = assert_invoke(app, ["show", task_id])
    assert "Story [red]urgent[/red] case" in result.output


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


def test_show_task_prints_description_with_brackets_literally() -> None:
    task_id = create_task("My story").task_id
    assert_invoke(
        app, ["edit", task_id, "--details", "fails when [red]config[/red] missing"]
    )
    result = assert_invoke(app, ["show", task_id])
    assert "Fails when [red]config[/red] missing" in result.output


def test_show_task_prints_extra_sections_with_brackets_literally(
    get_task_file: GetTaskFile,
) -> None:
    task_id = create_task("My story").task_id
    task_file = get_task_file(task_id)
    content = task_file.read_text()
    task_file.write_text(content + "\n## Examples\n\n- see [red]warning[/red] path\n")
    result = assert_invoke(app, ["show", task_id])
    assert "see [red]warning[/red] path" in result.output


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


def test_list_after_deleting_recent_task_does_not_crash() -> None:
    task_id = create_task("My story").task_id
    sub_id = add_subtask(task_id, "Subtask").task_id
    assert_invoke(app, ["start", sub_id])  # saves recent
    assert_invoke(app, ["move", sub_id, "--delete"])
    result = assert_invoke(app, ["list"])
    assert task_id in result.output


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


def test_list_todo_silently_skips_stale_ids() -> None:
    story_id = create_task("My story").task_id
    todo_sub = add_subtask(story_id, "Live todo").task_id

    repo = get_task_repo()
    save_todo_ids(repo, {todo_sub, "s99t99"})

    result = assert_invoke(app, ["list", "--todo"])
    assert todo_sub in result.output
    assert "s99t99" not in result.output


def test_list_todo_prunes_stale_ids_on_disk() -> None:
    story_id = create_task("My story").task_id
    todo_sub = add_subtask(story_id, "Live todo").task_id

    repo = get_task_repo()
    save_todo_ids(repo, {todo_sub, "s99t99"})

    assert_invoke(app, ["list", "--todo"])

    remaining = load_todo_ids(repo)
    assert remaining == {todo_sub}


def test_list_todo_lists_closed_todo_task() -> None:
    story_id = create_task("My story").task_id
    todo_sub = add_subtask(story_id, "Closed todo").task_id
    assert_invoke(app, ["todo", todo_sub])
    assert_invoke(app, ["done", todo_sub])

    result = assert_invoke(app, ["list", "--todo"])
    assert todo_sub in result.output


def test_list_todo_with_archived_rejects() -> None:
    create_task("My story")
    result = assert_invoke(app, ["list", "--todo", "--archived"], expect_error=True)
    assert "--todo" in result.output
    assert "--archived" in result.output


def test_list_todo_with_ref_is_additive_and_narrow() -> None:
    story1 = create_task("Story one").task_id
    todo_sub = add_subtask(story1, "Todo subtask").task_id
    sibling_of_todo = add_subtask(story1, "Sibling of todo").task_id

    story2 = create_task("Story two").task_id
    ref_sub = add_subtask(story2, "Ref subtask").task_id
    sibling_of_ref = add_subtask(story2, "Sibling of ref").task_id

    assert_invoke(app, ["todo", todo_sub])

    result = assert_invoke(app, ["list", "--todo", ref_sub])
    assert todo_sub in result.output
    assert ref_sub in result.output
    assert story1 in result.output
    assert story2 in result.output
    assert sibling_of_todo not in result.output
    assert sibling_of_ref not in result.output


def test_list_ref_hides_non_ref_siblings() -> None:
    story_id = create_task("My story").task_id
    target_sub = add_subtask(story_id, "Target subtask").task_id
    other_sub = add_subtask(story_id, "Other subtask").task_id

    result = assert_invoke(app, ["list", target_sub])
    assert target_sub in result.output
    assert story_id in result.output
    assert other_sub not in result.output


def test_list_todo_all_expands_closed_children_of_todo_task() -> None:
    story_id = create_task("My story").task_id
    todo_sub = add_subtask(story_id, "Todo subtask", details="d").task_id
    nested_done = add_subtask(todo_sub, "Nested done").task_id
    assert_invoke(app, ["done", nested_done])
    assert_invoke(app, ["todo", todo_sub])

    without_all = assert_invoke(app, ["list", "--todo"])
    assert nested_done not in without_all.output

    with_all = assert_invoke(app, ["list", "--todo", "--all"])
    assert nested_done in with_all.output


def test_list_todo_expands_open_children_of_todo_task() -> None:
    story_id = create_task("My story").task_id
    todo_sub = add_subtask(story_id, "Todo subtask", details="d").task_id
    nested_open = add_subtask(todo_sub, "Nested open").task_id
    assert_invoke(app, ["todo", todo_sub])

    result = assert_invoke(app, ["list", "--todo"])
    assert todo_sub in result.output
    assert nested_open in result.output


def test_list_todo_hides_non_todo_siblings() -> None:
    story_id = create_task("My story").task_id
    todo_sub = add_subtask(story_id, "Todo subtask").task_id
    other_sub = add_subtask(story_id, "Other open subtask").task_id
    assert_invoke(app, ["todo", todo_sub])

    result = assert_invoke(app, ["list", "--todo"])
    assert todo_sub in result.output
    assert story_id in result.output
    assert other_sub not in result.output


def test_list_todo_closed_todo_hides_non_todo_open_siblings() -> None:
    story_id = create_task("My story").task_id
    todo_sub = add_subtask(story_id, "Todo subtask").task_id
    other_sub = add_subtask(story_id, "Other open subtask").task_id
    assert_invoke(app, ["todo", todo_sub])
    assert_invoke(app, ["done", todo_sub])

    result = assert_invoke(app, ["list", "--todo"])
    assert todo_sub in result.output
    assert story_id in result.output
    assert other_sub not in result.output


def test_list_todo_multi_story_hides_non_todo_siblings() -> None:
    story1 = create_task("Story one").task_id
    todo1 = add_subtask(story1, "Todo one").task_id
    other1 = add_subtask(story1, "Open sibling one").task_id

    story2 = create_task("Story two").task_id
    todo2 = add_subtask(story2, "Todo two").task_id
    other2a = add_subtask(story2, "Open sibling two-a").task_id
    other2b = add_subtask(story2, "Open sibling two-b").task_id

    assert_invoke(app, ["todo", todo1])
    assert_invoke(app, ["todo", todo2])
    assert_invoke(app, ["done", todo2])

    result = assert_invoke(app, ["list", "--todo"])
    assert story1 in result.output
    assert story2 in result.output
    assert todo1 in result.output
    assert todo2 in result.output
    assert other1 not in result.output
    assert other2a not in result.output
    assert other2b not in result.output


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


# ---------------------------------------------------------------------------
# list --closed
# ---------------------------------------------------------------------------


def test_list_closed_shows_recently_done_task() -> None:
    story_id = create_task("My story").task_id
    sub_id = add_subtask(story_id, "Done subtask").task_id
    assert_invoke(app, ["done", sub_id])

    result = assert_invoke(app, ["list", "--closed"])
    assert sub_id in result.output
    assert "Done subtask" in result.output


def test_list_no_args_does_not_show_closed_task() -> None:
    story_id = create_task("My story").task_id
    sub_id = add_subtask(story_id, "Done subtask").task_id
    assert_invoke(app, ["done", sub_id])

    result = assert_invoke(app, ["list"])
    assert sub_id not in result.output


def test_list_closed_shows_multiple_tasks_from_history() -> None:
    story_id = create_task("My story").task_id
    sub1 = add_subtask(story_id, "First done").task_id
    sub2 = add_subtask(story_id, "Second done").task_id
    sub3 = add_subtask(story_id, "Third done").task_id
    assert_invoke(app, ["done", sub1])
    assert_invoke(app, ["done", sub2])
    assert_invoke(app, ["done", sub3])

    result = assert_invoke(app, ["list", "--closed"])
    # all three appear in the recently-closed view
    assert sub1 in result.output
    assert sub2 in result.output
    assert sub3 in result.output


def test_closed_history_reviewed_flag_appends(tasks_root: Path) -> None:
    story_id = create_task("Story").task_id
    sub_a = add_subtask(story_id, "Task A").task_id
    sub_b = add_subtask(story_id, "Task B").task_id
    assert_invoke(app, ["review", sub_a])
    assert_invoke(app, ["review", sub_b])
    assert_invoke(app, ["done", "--reviewed"])

    stored = (tasks_root / ".closed").read_text().splitlines()
    assert sub_a in stored
    assert sub_b in stored


def test_closed_history_multi_arg_done_preserves_order(tasks_root: Path) -> None:
    story_id = create_task("Story").task_id
    sub_a = add_subtask(story_id, "Task A").task_id
    sub_b = add_subtask(story_id, "Task B").task_id
    sub_c = add_subtask(story_id, "Task C").task_id
    assert_invoke(app, ["done", sub_b, sub_a, sub_c])

    stored = (tasks_root / ".closed").read_text().splitlines()
    assert stored == [sub_b, sub_a, sub_c]


def test_closed_history_force_excludes_forced_children(tasks_root: Path) -> None:
    story_id = create_task("Story").task_id
    sub_a = add_subtask(story_id, "Task A").task_id
    sub_b = add_subtask(story_id, "Task B").task_id
    assert_invoke(app, ["done", "--force", story_id])

    stored = (tasks_root / ".closed").read_text().splitlines()
    assert story_id in stored
    assert sub_a not in stored
    assert sub_b not in stored


def test_closed_history_dedup_on_reclose(tasks_root: Path) -> None:
    story_id = create_task("Story").task_id
    sub_a = add_subtask(story_id, "Task A").task_id
    sub_b = add_subtask(story_id, "Task B").task_id
    assert_invoke(app, ["done", sub_a])
    assert_invoke(app, ["done", sub_b])
    assert_invoke(app, ["reset", sub_a])
    assert_invoke(app, ["done", sub_a])

    stored = (tasks_root / ".closed").read_text().splitlines()
    # sub_a appears only once, and is now the newest
    assert stored.count(sub_a) == 1
    assert stored[-1] == sub_a
    assert stored == [sub_b, sub_a]


def test_list_closed_prunes_stale_ids(tasks_root: Path) -> None:
    story_id = create_task("Story").task_id
    sub_a = add_subtask(story_id, "Alive A").task_id
    sub_b = add_subtask(story_id, "Alive B").task_id

    (tasks_root / ".closed").write_text(f"s99t99\n{sub_a}\n{sub_b}\n")
    assert_invoke(app, ["list", "--closed"])

    stored = (tasks_root / ".closed").read_text().splitlines()
    assert "s99t99" not in stored
    assert sub_a in stored
    assert sub_b in stored


def test_list_closed_reaches_deeper_when_stale(tasks_root: Path) -> None:
    story_id = create_task("Story").task_id
    subs = [add_subtask(story_id, f"Task {i}").task_id for i in range(6)]

    ordered = ["s99t99", subs[0], subs[1], subs[2], subs[3], subs[4], subs[5]]
    (tasks_root / ".closed").write_text("\n".join(ordered) + "\n")

    result = assert_invoke(app, ["list", "--closed"])
    for i in range(1, 6):
        assert subs[i] in result.output
    assert "s99t99" not in result.output


def test_list_closed_all_shows_child_subtasks() -> None:
    story_id = create_task("My story").task_id
    sub_a = add_subtask(story_id, "Child A").task_id
    sub_b = add_subtask(story_id, "Child B").task_id
    assert_invoke(app, ["done", "--force", story_id])

    without_all = assert_invoke(app, ["list", "--closed"])
    assert sub_a not in without_all.output
    assert sub_b not in without_all.output

    with_all = assert_invoke(app, ["list", "--closed", "--all"])
    assert story_id in with_all.output
    assert sub_a in with_all.output
    assert sub_b in with_all.output


def test_list_closed_with_archived_rejects() -> None:
    create_task("Story")
    result = assert_invoke(app, ["list", "--closed", "--archived"], expect_error=True)
    assert "--closed" in result.output


def test_list_closed_with_todo_rejects() -> None:
    create_task("Story")
    result = assert_invoke(app, ["list", "--closed", "--todo"], expect_error=True)
    assert "--closed" in result.output


def test_list_closed_with_ref_rejects() -> None:
    story_id = create_task("Story").task_id
    result = assert_invoke(app, ["list", "--closed", story_id], expect_error=True)
    assert "--closed" in result.output


def test_list_closed_empty_shows_no_tasks_message() -> None:
    create_task("My story")
    result = assert_invoke(app, ["list", "--closed"])
    assert "No tasks to show" in result.output


def test_closed_history_capped_at_30(tasks_root: Path) -> None:
    story_id = create_task("Story").task_id
    sub_ids: list[str] = []
    for i in range(31):
        sub_ids.append(add_subtask(story_id, f"Task {i}").task_id)
    for sub_id in sub_ids:
        assert_invoke(app, ["done", sub_id])

    stored = (tasks_root / ".closed").read_text().splitlines()
    assert len(stored) == 30
    # oldest (sub_ids[0]) is evicted; newest (sub_ids[30]) is the last line
    assert sub_ids[0] not in stored
    assert stored[-1] == sub_ids[30]
