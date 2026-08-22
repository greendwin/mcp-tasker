import json
from pathlib import Path

from tasker.cli import app, get_task_repo
from tasker.todo import load_todo_list, save_todo_list

from .helpers import GetTaskFile, add_subtask, assert_invoke, create_task


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


def test_show_task_prints_body_sections_with_brackets_literally(
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
    save_todo_list(repo, [todo_sub, "s99t99"])

    result = assert_invoke(app, ["list", "--todo"])
    assert todo_sub in result.output
    assert "s99t99" not in result.output


def test_list_todo_prunes_stale_ids_on_disk() -> None:
    story_id = create_task("My story").task_id
    todo_sub = add_subtask(story_id, "Live todo").task_id

    repo = get_task_repo()
    save_todo_list(repo, [todo_sub, "s99t99"])

    assert_invoke(app, ["list", "--todo"])

    remaining = load_todo_list(repo)
    assert remaining == [todo_sub]


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


def test_list_todo_expands_children_of_all_sibling_todo_tasks() -> None:
    # regression: when several todo tasks share a parent, the parent is added
    # to the show config (MANUAL mode) between the siblings. Processing order
    # must not let the parent mark a later sibling as walked before that
    # sibling expands its own children -- nor must it over-expand non-todo
    # siblings that share the same parent.
    story_id = create_task("My story").task_id

    todo_a = add_subtask(story_id, "Todo A", details="d").task_id
    nested_a = add_subtask(todo_a, "Nested under A").task_id

    todo_b = add_subtask(story_id, "Todo B", details="d").task_id
    nested_b = add_subtask(todo_b, "Nested under B").task_id

    todo_c = add_subtask(story_id, "Todo C", details="d").task_id
    nested_c = add_subtask(todo_c, "Nested under C").task_id

    # non-todo sibling with its own child: must stay hidden (no over-expansion)
    other = add_subtask(story_id, "Other open subtask", details="d").task_id
    nested_other = add_subtask(other, "Nested under other").task_id

    assert_invoke(app, ["todo", todo_a])
    assert_invoke(app, ["todo", todo_b])
    assert_invoke(app, ["todo", todo_c])

    result = assert_invoke(app, ["list", "--todo"])
    # every todo sibling expands its own child, regardless of processing order
    assert nested_a in result.output
    assert nested_b in result.output
    assert nested_c in result.output
    # the non-todo sibling and its child remain hidden
    assert other not in result.output
    assert nested_other not in result.output


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


def test_list_todo_all_finished_no_highlight() -> None:
    story_id = create_task("My story").task_id
    sub = add_subtask(story_id, "Done todo").task_id
    assert_invoke(app, ["todo", sub])
    assert_invoke(app, ["done", sub])

    result = assert_invoke(app, ["list", "--todo"])
    assert "All tasks finished!" in result.output
    assert sub in result.output
    assert "<<<" not in result.output


def test_list_todo_all_with_mixed_shows_everything_no_footer() -> None:
    story_id = create_task("My story").task_id
    active_sub = add_subtask(story_id, "Active todo").task_id
    finished_sub = add_subtask(story_id, "Finished todo").task_id
    assert_invoke(app, ["todo", active_sub])
    assert_invoke(app, ["todo", finished_sub])
    assert_invoke(app, ["done", finished_sub])

    result = assert_invoke(app, ["list", "--todo", "--all"])
    assert active_sub in result.output
    assert finished_sub in result.output
    assert "hidden" not in result.output
    assert "All tasks finished" not in result.output
    assert "<<<" not in result.output


def test_list_todo_with_explicit_ref_does_not_filter_ref() -> None:
    story_id = create_task("My story").task_id
    active_sub = add_subtask(story_id, "Active todo").task_id
    finished_sub = add_subtask(story_id, "Finished todo").task_id
    assert_invoke(app, ["todo", active_sub])
    assert_invoke(app, ["todo", finished_sub])
    assert_invoke(app, ["done", finished_sub])

    other_story = create_task("Other story").task_id
    other_done = add_subtask(other_story, "Other done").task_id
    assert_invoke(app, ["done", other_done])

    result = assert_invoke(app, ["list", "--todo", other_done])
    assert other_done in result.output
    assert active_sub in result.output
    assert finished_sub not in result.output


def test_list_todo_empty_falls_back_to_open_tasks() -> None:
    story = create_task("Active story").task_id
    add_subtask(story, "Open subtask")

    result = assert_invoke(app, ["list", "--todo"])
    assert "Open tasks:" in result.output
    assert "Active story" in result.output
    assert "Open subtask" in result.output


def test_list_todo_all_finished_keeps_finished_message() -> None:
    story = create_task("My story").task_id
    finished_sub = add_subtask(story, "Finished todo").task_id
    assert_invoke(app, ["todo", finished_sub])
    assert_invoke(app, ["done", finished_sub])

    result = assert_invoke(app, ["list", "--todo"])
    assert "All tasks finished" in result.output
    assert "Open tasks:" not in result.output


def test_list_todo_empty_fallback_excludes_closed_roots() -> None:
    closed_story = create_task("Closed story").task_id
    assert_invoke(app, ["done", "--force", closed_story])

    result = assert_invoke(app, ["list", "--todo"])
    assert closed_story not in result.output
    assert "No tasks to show" in result.output


def test_list_todo_empty_announces_empty_todo_list() -> None:
    story = create_task("Active story").task_id
    add_subtask(story, "Open subtask")

    result = assert_invoke(app, ["list", "--todo"])
    assert "Todo list is empty." in result.output
    assert "Open tasks:" in result.output


def test_list_todo_all_empty_fallback_ignores_all_flag() -> None:
    story = create_task("Active story").task_id
    add_subtask(story, "Open subtask")

    result = assert_invoke(app, ["list", "--todo", "--all"])
    assert "Open tasks:" in result.output
    # the --all flag must not leak pending markers onto the fallback listing
    assert "[ ]" not in result.output


def test_list_todo_all_shows_finished_message_when_all_done() -> None:
    story = create_task("My story").task_id
    finished_sub = add_subtask(story, "Finished todo").task_id
    assert_invoke(app, ["todo", finished_sub])
    assert_invoke(app, ["done", finished_sub])

    result = assert_invoke(app, ["list", "--todo", "--all"])
    assert "All tasks finished" in result.output


def test_list_rev_shows_in_review_tasks_across_roots() -> None:
    story_a = create_task("Story A").task_id
    sub_a = add_subtask(story_a, "Subtask A").task_id
    story_b = create_task("Story B").task_id
    sub_b = add_subtask(story_b, "Subtask B").task_id
    add_subtask(story_b, "Open subtask")
    assert_invoke(app, ["review", sub_a])
    assert_invoke(app, ["review", sub_b])

    result = assert_invoke(app, ["list", "--rev"])
    assert sub_a in result.output
    assert sub_b in result.output
    assert "Subtask A" in result.output
    assert "Subtask B" in result.output


def test_list_in_review_alias_matches_rev() -> None:
    story = create_task("Story").task_id
    sub = add_subtask(story, "Reviewable").task_id
    assert_invoke(app, ["review", sub])

    result = assert_invoke(app, ["list", "--in-review"])
    assert sub in result.output
    assert "Reviewable" in result.output


def test_list_rev_empty_falls_back_with_green_header() -> None:
    story = create_task("Active story").task_id
    add_subtask(story, "Open subtask")

    result = assert_invoke(app, ["list", "--rev"])
    assert "No tasks in review" in result.output
    assert story in result.output
    assert "Active story" in result.output


def test_list_rev_empty_fallback_excludes_closed_roots() -> None:
    open_story = create_task("Open story").task_id
    closed_story = create_task("Closed story").task_id
    assert_invoke(app, ["done", "--force", closed_story])

    result = assert_invoke(app, ["list", "--rev"])
    assert "No tasks in review" in result.output
    assert open_story in result.output
    assert closed_story not in result.output


def test_list_rev_empty_fallback_shows_open_tasks_header() -> None:
    story = create_task("Active story").task_id
    add_subtask(story, "Open subtask")

    result = assert_invoke(app, ["list", "--rev"])
    assert "No tasks in review" in result.output
    assert "Open tasks:" in result.output
    assert "Active story" in result.output


def test_list_rev_todo_fallback_omits_open_tasks_header() -> None:
    story = create_task("Active story").task_id
    pinned = add_subtask(story, "Pinned subtask").task_id
    add_subtask(story, "Other open")
    assert_invoke(app, ["todo", pinned])

    result = assert_invoke(app, ["list", "--rev"])
    # the todo-list fallback must not be mislabelled as the open-tasks listing
    assert "Showing todo list:" in result.output
    assert "Open tasks:" not in result.output


def test_list_rev_all_empty_fallback_ignores_all_flag() -> None:
    story = create_task("Active story").task_id
    add_subtask(story, "Open subtask")

    result = assert_invoke(app, ["list", "--rev", "--all"])
    assert "Open tasks:" in result.output
    # the --all flag must not leak pending markers onto the fallback listing
    assert "[ ]" not in result.output


def test_list_rev_all_todo_fallback_ignores_all_flag() -> None:
    story = create_task("Active story").task_id
    pinned = add_subtask(story, "Pinned subtask").task_id
    assert_invoke(app, ["todo", pinned])

    result = assert_invoke(app, ["list", "--rev", "--all"])
    assert "Showing todo list:" in result.output
    # the --all flag must not leak pending markers onto the todo-list fallback
    assert "[ ]" not in result.output


def test_list_rev_with_refs_is_additive_and_show_no_review() -> None:
    story = create_task("Story").task_id
    open_sub = add_subtask(story, "Open subtask").task_id

    result = assert_invoke(app, ["list", "--rev", open_sub])
    assert open_sub in result.output
    assert "No tasks in review" in result.output


def test_list_rev_with_archived_rejects() -> None:
    create_task("Story")
    result = assert_invoke(app, ["list", "--rev", "--archived"], expect_error=True)
    assert "--in-review" in result.output


def test_list_rev_with_todo_rejects() -> None:
    create_task("Story")
    result = assert_invoke(app, ["list", "--rev", "--todo"], expect_error=True)
    assert "--in-review" in result.output


def test_list_rev_with_closed_rejects() -> None:
    create_task("Story")
    result = assert_invoke(app, ["list", "--rev", "--closed"], expect_error=True)
    assert "--in-review" in result.output


def test_list_rev_falls_back_to_todo_when_active_pinned() -> None:
    story = create_task("Active story").task_id
    pinned = add_subtask(story, "Pinned subtask").task_id
    other_open = add_subtask(story, "Other open").task_id
    assert_invoke(app, ["todo", pinned])

    result = assert_invoke(app, ["list", "--rev"])
    assert "No tasks in review" in result.output
    assert "Showing todo list" in result.output
    assert pinned in result.output
    assert "Pinned subtask" in result.output
    assert other_open not in result.output


def test_list_rev_todo_fallback_uses_letter_marker() -> None:
    story = create_task("Story").task_id
    pinned = add_subtask(story, "Pinned subtask").task_id
    assert_invoke(app, ["todo", pinned])

    result = assert_invoke(app, ["list", "--rev"])
    assert "(ta)" in result.output


def test_list_rev_skips_todo_fallback_when_all_pinned_finished() -> None:
    story = create_task("Story").task_id
    pinned = add_subtask(story, "Pinned subtask").task_id
    other_open = add_subtask(story, "Other open").task_id
    assert_invoke(app, ["todo", pinned])
    assert_invoke(app, ["done", pinned])

    result = assert_invoke(app, ["list", "--rev"])
    assert "No tasks in review" in result.output
    assert "Showing todo list" not in result.output
    assert other_open in result.output


def test_list_rev_todo_fallback_additive_refs() -> None:
    story_a = create_task("Story A").task_id
    pinned = add_subtask(story_a, "Pinned subtask").task_id
    assert_invoke(app, ["todo", pinned])

    story_b = create_task("Story B").task_id
    ref_sub = add_subtask(story_b, "Ref subtask").task_id

    result = assert_invoke(app, ["list", "--rev", ref_sub])
    assert "No tasks in review" in result.output
    assert "Showing todo list" in result.output
    assert pinned in result.output
    assert ref_sub in result.output
