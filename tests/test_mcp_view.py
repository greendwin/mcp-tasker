import pytest

from tasker.base_types import TaskStatus
from tasker.cli import app, get_task_repo
from tasker.exceptions import TaskValidateError
from tasker.mcp import (
    TaskInfo,
    TaskPreview,
    finish_task,
    list_tasks,
    start_task,
    view_tasks,
)
from tasker.todo import load_todo_ids, save_todo_ids

from .helpers import add_subtask, assert_invoke, create_task


def test_list_tasks_returns_empty() -> None:
    result = list_tasks()
    assert result == []


def test_list_tasks_returns_task() -> None:
    task_id = create_task("My story").task_id
    result = list_tasks()
    assert len(result) == 1
    assert result[0].id == task_id
    assert result[0].title == "My story"
    assert result[0].status == TaskStatus.PENDING


def test_list_tasks_returns_task_preview_instances() -> None:
    create_task("My story")
    result = list_tasks()
    assert type(result[0]) is TaskPreview


def test_list_tasks_multiple_root_tasks() -> None:
    create_task("First story")
    create_task("Second story")
    result = list_tasks()
    assert len(result) == 2
    titles = {t.title for t in result}
    assert titles == {"First story", "Second story"}


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


def test_view_tasks_no_description_is_none() -> None:
    task_id = create_task("My story").task_id
    result = view_tasks([task_id])[0]
    assert result.description is None


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
    assert len(result) == 1
    assert result[0].id == s1


def test_list_tasks_todo_empty() -> None:
    create_task("Story one")
    result = list_tasks(todo=True)
    assert result == []


def test_list_tasks_todo_silently_skips_and_prunes_stale_ids() -> None:
    s1 = create_task("Story one").task_id
    repo = get_task_repo()
    save_todo_ids(repo, {s1, "s99t99"})

    result = list_tasks(todo=True)
    assert len(result) == 1
    assert result[0].id == s1

    remaining = load_todo_ids(repo)
    assert remaining == {s1}
