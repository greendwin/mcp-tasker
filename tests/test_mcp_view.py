from tasker.cli import app, get_task_repo
from tasker.mcp import (
    finish_task,
    list_tasks,
    review_task,
    start_task,
    view_tasks,
)
from tasker.mcp._render import TASK_BLOCK_SEPARATOR
from tasker.todo import load_todo_list, save_todo_list

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


# --- view_tasks markdown rendering ---


def test_view_tasks_renders_heading_status_and_body() -> None:
    task_id = create_task("My story").task_id
    sub = add_subtask(task_id, "Sub", "Some details")

    result = view_tasks([sub.task_ref])
    assert isinstance(result, str)
    assert f"# {sub.task_id}: Sub" in result
    assert "status: pending" in result
    assert "Some details" in result


def test_view_tasks_renders_full_untruncated_title() -> None:
    long_title = (
        "A very long task title that exceeds the sixty character limit by quite a lot"
    )
    assert len(long_title) > 60
    task_id = create_task(long_title).task_id

    result = view_tasks([task_id])
    assert f"# {task_id}: {long_title}" in result
    assert "..." not in result


def test_view_tasks_root_omits_parent_line() -> None:
    task_id = create_task("My story").task_id
    result = view_tasks([task_id])
    assert "parent:" not in result


def test_view_tasks_subtask_includes_parent_line() -> None:
    parent_id = create_task("My story").task_id
    sub = add_subtask(parent_id, "Sub")
    result = view_tasks([sub.task_ref])
    assert f"parent: {parent_id}" in result


def test_view_tasks_body_section_only_renders_verbatim(
    get_task_file: GetTaskFile,
) -> None:
    task_id = create_task("My story").task_id
    path = get_task_file(task_id)
    path.write_text(path.read_text() + "\n## Notes\n\nSome notes here.\n")

    result = view_tasks([task_id])
    assert "## Notes\n\nSome notes here." in result


def test_view_tasks_no_subtasks_omits_subtasks_section() -> None:
    task_id = create_task("My story").task_id
    result = view_tasks([task_id])
    assert "## Subtasks" not in result


def test_view_tasks_lists_subtasks_with_status_signs() -> None:
    task_id = create_task("My story").task_id
    sub_pending_id = add_subtask(task_id, "Pending sub").task_id
    sub_inprog = add_subtask(task_id, "Started sub")
    sub_done = add_subtask(task_id, "Done sub")
    sub_review = add_subtask(task_id, "Review sub")
    start_task(sub_inprog.task_ref)
    finish_task(sub_done.task_ref)
    review_task(sub_review.task_ref)

    result = view_tasks([task_id])
    assert "## Subtasks" in result
    assert f". {sub_pending_id}" in result
    assert f"~ {sub_inprog.task_id}" in result
    assert f"x {sub_done.task_id}" in result
    assert f"? {sub_review.task_id}" in result


def test_view_tasks_bad_ref_does_not_raise() -> None:
    result = view_tasks(["s99"])
    assert result.startswith("# s99: ")
    assert "not found" in result


def test_view_tasks_batch_mixes_good_and_bad_refs() -> None:
    task_id = create_task("Good story").task_id
    result = view_tasks([task_id, "s99"])

    blocks = result.split(TASK_BLOCK_SEPARATOR)
    assert len(blocks) == 2
    assert f"# {task_id}: Good story" in result
    assert "# s99: " in result
    assert "not found" in result


def test_view_tasks_empty_list_returns_empty_string() -> None:
    assert view_tasks([]) == ""


def test_view_tasks_embedded_headings_survive_and_do_not_split() -> None:
    parent_id = create_task("Parent story").task_id
    sub = add_subtask(
        parent_id,
        "Child",
        "# Embedded heading\n\n## Embedded sub\n\nText.",
    )

    result = view_tasks([parent_id, sub.task_ref])
    blocks = result.split(TASK_BLOCK_SEPARATOR)
    assert len(blocks) == 2

    child_block = blocks[1]
    assert "# Embedded heading" in child_block
    assert "## Embedded sub" in child_block
    assert "Text." in child_block


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
    save_todo_list(repo, [s1, "s99t99"])

    result = list_tasks(todo=True)
    assert isinstance(result, str)
    assert s1 in result

    remaining = load_todo_list(repo)
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
    result = view_tasks(["ta"])
    assert f"# {s1}: Story one" in result


def test_view_tasks_resolves_t_letter_with_child_digits() -> None:
    s1 = create_task("Story one").task_id
    sub_id = add_subtask(s1, "Child").task_id
    assert_invoke(app, ["todo", s1])
    result = view_tasks(["ta01"])
    assert f"# {sub_id}: Child" in result


def test_view_tasks_resolves_q_shortcut() -> None:
    s1 = create_task("Story one").task_id
    assert_invoke(app, ["show", s1])
    result = view_tasks(["q"])
    assert f"# {s1}: Story one" in result


def test_view_tasks_shortcut_does_not_update_recent() -> None:
    s1 = create_task("Story one").task_id
    s2 = create_task("Story two").task_id
    assert_invoke(app, ["todo", s1])
    assert_invoke(app, ["show", s2])  # set recent to s2
    view_tasks(["ta"])  # access via shortcut
    result = view_tasks(["q"])
    assert f"# {s2}: Story two" in result


# --- body marker in list output ---


def test_list_tasks_shows_body_marker(get_task_file: GetTaskFile) -> None:
    task_id = create_task("Story with body").task_id
    path = get_task_file(task_id)
    path.write_text(path.read_text() + "\n## Notes\n\nSome notes here.\n")
    result = list_tasks()
    assert "(...)" in result
