import pytest

from tasker.base_types import TaskStatus
from tasker.cli import app, get_task_repo
from tasker.exceptions import TaskValidateError
from tasker.mcp import (
    TaskInfo,
    finish_task,
    list_tasks,
    start_task,
    view_tasks,
)
from tasker.todo import load_todo_ids, save_todo_ids

from .helpers import GetTaskFile, add_subtask, assert_invoke, create_task


def test_list_tasks_returns_empty() -> None:
    result = list_tasks()
    assert result == "No tasks"


def test_list_tasks_returns_task() -> None:
    task_id = create_task("My story").task_id
    result = list_tasks()
    assert isinstance(result, str)
    assert task_id in result
    assert "My story" in result
    assert result.startswith(". ")


def test_list_tasks_returns_string() -> None:
    create_task("My story")
    result = list_tasks()
    assert isinstance(result, str)


def test_list_tasks_multiple_root_tasks() -> None:
    create_task("First story")
    create_task("Second story")
    result = list_tasks()
    assert isinstance(result, str)
    assert "First story" in result
    assert "Second story" in result


def test_view_tasks_returns_task_info() -> None:
    task_id = create_task("My story").task_id
    result = view_tasks([task_id])[0]
    assert isinstance(result, TaskInfo)
    assert result.id == task_id
    assert result.title == "My story"
    assert result.status == TaskStatus.PENDING
    assert result.subtasks == {}


def test_view_tasks_includes_description() -> None:
    task_id = create_task("My story").task_id
    sub_ref = add_subtask(task_id, "Sub", "Some details").task_ref
    result = view_tasks([sub_ref])[0]
    assert result.description == "Some details"


def test_view_tasks_has_no_has_body_field() -> None:
    # has_body is a list-row affordance; the detailed view carries the body
    # itself, so the detail model must not declare a (always-false) has_body field.
    assert "has_body" not in TaskInfo.model_fields


def test_view_tasks_no_description_is_none() -> None:
    task_id = create_task("My story").task_id
    result = view_tasks([task_id])[0]
    assert result.description is None


def test_view_tasks_body_is_section_only(get_task_file: GetTaskFile) -> None:
    task_id = create_task("My story").task_id
    path = get_task_file(task_id)
    path.write_text(path.read_text() + "\n## Notes\n\nSome notes here.\n")

    result = view_tasks([task_id])[0]
    assert result.description == "## Notes\n\nSome notes here."


def test_view_tasks_body_includes_lead_and_sections(
    get_task_file: GetTaskFile,
) -> None:
    task_id = create_task("My story").task_id
    path = get_task_file(task_id)
    content = path.read_text()
    content = content.replace(
        "# My story\n",
        "# My story\n\nSome details.\n\n## Notes\n\nSome notes here.\n",
    )
    path.write_text(content)

    result = view_tasks([task_id])[0]
    assert result.description == "Some details.\n\n## Notes\n\nSome notes here."


def test_view_tasks_subtasks_grouped_by_status() -> None:
    task_id = create_task("My story").task_id
    sub_id = add_subtask(task_id, "Sub").task_id
    result = view_tasks([task_id])[0]
    assert result.subtasks == {"pending": [sub_id]}


def test_view_tasks_subtasks_values_are_id_strings() -> None:
    task_id = create_task("My story").task_id
    add_subtask(task_id, "Sub")
    result = view_tasks([task_id])[0]
    # subtask values are plain strings (IDs), not objects
    assert isinstance(result.subtasks["pending"][0], str)


def test_view_tasks_subtasks_multiple_statuses() -> None:
    task_id = create_task("My story").task_id
    sub1_id = add_subtask(task_id, "Pending sub").task_id
    sub2_ref = add_subtask(task_id, "Started sub").task_ref
    sub3_ref = add_subtask(task_id, "Done sub").task_ref
    start_task(sub2_ref)
    finish_task(sub3_ref)
    result = view_tasks([task_id])[0]
    assert result.subtasks["pending"] == [sub1_id]
    assert len(result.subtasks["in-progress"]) == 1
    assert len(result.subtasks["done"]) == 1


def test_view_tasks_not_found_raises() -> None:
    with pytest.raises(TaskValidateError):
        view_tasks(["s99"])


def test_view_tasks_returns_multiple() -> None:
    id1 = create_task("First").task_id
    id2 = create_task("Second").task_id
    results = view_tasks([id1, id2])
    assert len(results) == 2
    ids = {r.id for r in results}
    assert ids == {id1, id2}


def test_view_tasks_empty_list() -> None:
    assert view_tasks([]) == []


def test_view_tasks_returns_task_info_instances() -> None:
    task_id = create_task("Story").task_id
    results = view_tasks([task_id])
    assert isinstance(results[0], TaskInfo)


# --- list_tasks with todo filter ---


def test_list_tasks_todo_returns_todo_tasks() -> None:
    s1 = create_task("Story one").task_id
    create_task("Story two")
    assert_invoke(app, ["todo", s1])
    result = list_tasks(todo=True)
    assert isinstance(result, str)
    assert s1 in result
    assert "Story one" in result


def test_list_tasks_todo_empty() -> None:
    create_task("Story one")
    result = list_tasks(todo=True)
    assert result == "No tasks"


def test_list_tasks_todo_silently_skips_and_prunes_stale_ids() -> None:
    s1 = create_task("Story one").task_id
    repo = get_task_repo()
    save_todo_ids(repo, [s1, "s99t99"])

    result = list_tasks(todo=True)
    assert isinstance(result, str)
    assert s1 in result

    remaining = load_todo_ids(repo)
    assert remaining == [s1]


def test_list_tasks_todo_excludes_finished_tasks() -> None:
    s1 = create_task("Open story").task_id
    s2 = create_task("Done story").task_id
    assert_invoke(app, ["todo", s1])
    assert_invoke(app, ["todo", s2])
    finish_task(s2)
    result = list_tasks(todo=True)
    assert isinstance(result, str)
    assert "Open story" in result
    assert "Done story" not in result


def test_list_tasks_todo_all_finished() -> None:
    s1 = create_task("Story one").task_id
    assert_invoke(app, ["todo", s1])
    finish_task(s1)
    result = list_tasks(todo=True)
    assert result == "All tasks finished!"


# --- shortcut resolution in MCP ---


def test_view_tasks_resolves_t_letter_shortcut() -> None:
    s1 = create_task("Story one").task_id
    create_task("Story two")
    assert_invoke(app, ["todo", s1])
    result = view_tasks(["ta"])[0]
    assert result.id == s1
    assert result.title == "Story one"


def test_view_tasks_resolves_t_letter_with_child_digits() -> None:
    s1 = create_task("Story one").task_id
    sub_id = add_subtask(s1, "Child").task_id
    assert_invoke(app, ["todo", s1])
    result = view_tasks(["ta01"])[0]
    assert result.id == sub_id


def test_view_tasks_resolves_q_shortcut() -> None:
    s1 = create_task("Story one").task_id
    assert_invoke(app, ["show", s1])
    result = view_tasks(["q"])[0]
    assert result.id == s1


def test_view_tasks_shortcut_does_not_update_recent() -> None:
    s1 = create_task("Story one").task_id
    s2 = create_task("Story two").task_id
    assert_invoke(app, ["todo", s1])
    assert_invoke(app, ["show", s2])  # set recent to s2
    view_tasks(["ta"])  # access via shortcut
    result = view_tasks(["q"])[0]
    assert result.id == s2


# --- body marker in list output ---


def test_list_tasks_shows_body_marker(get_task_file: GetTaskFile) -> None:
    task_id = create_task("Story with body").task_id
    path = get_task_file(task_id)
    path.write_text(path.read_text() + "\n## Notes\n\nSome notes here.\n")
    result = list_tasks()
    assert "(...)" in result
