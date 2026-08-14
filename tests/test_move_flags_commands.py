import json
import re
from pathlib import Path
from unittest import mock

import pytest

from tasker.cli import app
from tasker.parse import parse_task_file

from .helpers import GetTaskFile, add_subtask, assert_invoke, create_task


@pytest.fixture()
def s1() -> str:
    return create_task("Story one").task_id


@pytest.fixture()
def s2() -> str:
    return create_task("Story two").task_id


# ---------------------------------------------------------------------------
# move --delete
# ---------------------------------------------------------------------------


def test_delete_inline_subtask(s1: str, get_task_file: GetTaskFile) -> None:
    add_subtask(s1, "Task A")
    add_subtask(s1, "Task B")
    result = assert_invoke(app, ["move", f"{s1}t01", "--delete"])
    assert "deleted" in result.output

    content = get_task_file(s1).read_text()
    assert "Task A" not in content
    assert "Task B" in content


def test_delete_file_subtask(s1: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Task A", details="Has details").task_id
    story_dir = next(tasks_root.glob(f"{s1}-*/"))
    old_file = next(story_dir.glob(f"{t01}-*.md"))
    assert old_file.exists()

    result = assert_invoke(app, ["move", t01, "--delete"])
    assert "deleted" in result.output
    assert not old_file.exists()


def test_delete_extended_subtask(s1: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Container", details="Details").task_id
    add_subtask(t01, "Child", details="Child details")
    story_dir = next(tasks_root.glob(f"{s1}-*/"))
    old_dir = next(story_dir.glob(f"{t01}-*/"))
    assert old_dir.is_dir()

    assert_invoke(app, ["move", t01, "--delete"])
    assert not old_dir.exists()


def test_delete_root_task(s1: str, tasks_root: Path) -> None:
    old_file = next(tasks_root.glob(f"{s1}-*.md"))
    assert old_file.exists()

    result = assert_invoke(app, ["move", s1, "--delete"])
    assert "deleted" in result.output
    assert not old_file.exists()


def test_delete_multiple_tasks(s1: str) -> None:
    add_subtask(s1, "Task A")
    add_subtask(s1, "Task B")
    result = assert_invoke(app, ["move", f"{s1}t01", f"{s1}t02", "--delete"])
    assert "deleted" in result.output


def test_delete_json_output(s1: str) -> None:
    add_subtask(s1, "Task A")
    result = assert_invoke(app, ["--json-output", "move", f"{s1}t01", "--delete"])
    data = json.loads(result.output)
    assert "task_refs" in data


def test_delete_parent_downgrades(s1: str, tasks_root: Path) -> None:
    """Deleting the only file-based subtask should downgrade parent."""
    t01 = add_subtask(s1, "File task", details="Has details").task_id

    src_dirs = list(tasks_root.glob(f"{s1}-*/"))
    assert len(src_dirs) == 1
    assert src_dirs[0].is_dir()

    assert_invoke(app, ["move", t01, "--delete"])

    # source should downgrade to basic file
    src_files = list(tasks_root.glob(f"{s1}-*.md"))
    assert len(src_files) == 1
    assert src_files[0].is_file()


def test_delete_rejects_with_parent_flag(s1: str, s2: str) -> None:
    t01 = add_subtask(s1, "Task").task_id
    result = assert_invoke(
        app, ["move", t01, "--delete", "--parent", s2], expect_error=True
    )
    assert "only one" in result.output.lower()


def test_delete_rejects_with_root_flag(s1: str) -> None:
    t01 = add_subtask(s1, "Task").task_id
    result = assert_invoke(app, ["move", t01, "--delete", "--root"], expect_error=True)
    assert "only one" in result.output.lower()


def test_delete_shows_preview_with_parent(s1: str) -> None:
    """Deleting a subtask should show the parent preview with deleted task."""
    add_subtask(s1, "Task A")
    add_subtask(s1, "Task B")
    result = assert_invoke(app, ["move", f"{s1}t01", "--delete"])
    # preview should show parent with remaining and deleted tasks
    assert "Story one" in result.output
    assert "Task A" in result.output
    assert "Task B" in result.output


def test_delete_preview_not_listed_as_subtask_text(s1: str) -> None:
    """No 'Deleted subtasks:' section — preview handles it."""
    add_subtask(s1, "Task A")
    result = assert_invoke(app, ["move", f"{s1}t01", "--delete"])
    assert "Deleted subtasks:" not in result.output


# ---------------------------------------------------------------------------
# move --editor
# ---------------------------------------------------------------------------


def test_move_editor_calls_editor(s1: str, s2: str, run_editor: mock.Mock) -> None:
    t01 = add_subtask(s1, "Task A").task_id
    assert_invoke(app, ["move", t01, "--parent", s2, "--editor"])
    assert run_editor.call_count == 1


def test_move_editor_short_flag(s1: str, s2: str, run_editor: mock.Mock) -> None:
    t01 = add_subtask(s1, "Task A").task_id
    assert_invoke(app, ["move", t01, "--parent", s2, "-e"])
    assert run_editor.call_count == 1


def test_move_editor_opens_moved_task(s1: str, s2: str, run_editor: mock.Mock) -> None:
    t01 = add_subtask(s1, "Task A").task_id
    assert_invoke(app, ["move", t01, "--parent", s2, "-e"])
    opened_path: Path = run_editor.call_args[0][0]
    assert opened_path.exists()
    content = opened_path.read_text()
    assert "Task A" in content


def test_move_root_editor_opens_promoted_task(s1: str, run_editor: mock.Mock) -> None:
    t01 = add_subtask(s1, "Task A", details="some desc").task_id
    assert_invoke(app, ["move", t01, "--root", "-e"])
    opened_path: Path = run_editor.call_args[0][0]
    assert opened_path.exists()
    content = opened_path.read_text()
    assert "Task A" in content


def test_move_editor_opens_each_moved_task(
    s1: str, s2: str, run_editor: mock.Mock
) -> None:
    add_subtask(s1, "Task A")
    add_subtask(s1, "Task B")
    assert_invoke(app, ["move", f"{s1}t01", f"{s1}t02", "--parent", s2, "-e"])
    assert run_editor.call_count == 2


def test_move_delete_editor_errors(s1: str) -> None:
    add_subtask(s1, "Task A")
    result = assert_invoke(
        app, ["move", f"{s1}t01", "--delete", "-e"], expect_error=True
    )
    assert "--editor cannot be used with --delete" in result.output


# ---------------------------------------------------------------------------
# move --id
# ---------------------------------------------------------------------------


def test_move_id_same_parent_renames(s1: str) -> None:
    add_subtask(s1, "Task A")
    t02 = add_subtask(s1, "Task B").task_id
    # rename t02 to a free sibling id under the same parent
    result = assert_invoke(app, ["move", t02, "--id", f"{s1}t09"])
    assert "renamed to" in result.output
    assert f"{s1}t09" in result.output


def test_move_id_to_root(s1: str) -> None:
    t01 = add_subtask(s1, "Promote me").task_id
    result = assert_invoke(app, ["move", t01, "--id", "s09"])
    assert "moved to root" in result.output
    assert "s09" in result.output


def test_move_id_to_other_parent(s1: str, s2: str) -> None:
    t01 = add_subtask(s1, "Task A").task_id
    result = assert_invoke(app, ["move", t01, "--id", f"{s2}t01"])
    assert "moved under" in result.output
    assert s2 in result.output


def test_move_id_with_parent_errors(s1: str, s2: str) -> None:
    t01 = add_subtask(s1, "Task A").task_id
    result = assert_invoke(
        app, ["move", t01, "--id", f"{s2}t01", "--parent", s2], expect_error=True
    )
    assert "only one" in result.output.lower()


def test_move_id_with_root_errors(s1: str) -> None:
    t01 = add_subtask(s1, "Task A").task_id
    result = assert_invoke(
        app, ["move", t01, "--id", "s09", "--root"], expect_error=True
    )
    assert "only one" in result.output.lower()


def test_move_id_with_delete_errors(s1: str) -> None:
    t01 = add_subtask(s1, "Task A").task_id
    result = assert_invoke(
        app, ["move", t01, "--id", "s09", "--delete"], expect_error=True
    )
    assert "only one" in result.output.lower()


def test_move_id_two_refs_errors(s1: str) -> None:
    t01 = add_subtask(s1, "Task A").task_id
    t02 = add_subtask(s1, "Task B").task_id
    result = assert_invoke(
        app, ["move", t01, t02, "--id", f"{s1}t09"], expect_error=True
    )
    assert result.exit_code != 0
    assert "single task ref" in result.output


def test_move_id_occupied_target_errors(s1: str) -> None:
    t01 = add_subtask(s1, "Task A").task_id
    add_subtask(s1, "Task B")
    result = assert_invoke(app, ["move", t01, "--id", f"{s1}t02"], expect_error=True)
    assert result.exit_code != 0
    assert "already taken" in result.output


def test_move_id_missing_parent_errors(s1: str) -> None:
    t01 = add_subtask(s1, "Task A").task_id
    result = assert_invoke(app, ["move", t01, "--id", "s99t01"], expect_error=True)
    assert result.exit_code != 0
    assert "s99" in result.output
    assert "not found" in result.output


def test_move_id_idempotent_target(s1: str) -> None:
    t01 = add_subtask(s1, "Task A").task_id
    result = assert_invoke(app, ["move", t01, "--id", t01])
    assert "already" in result.output.lower()
    assert "Renamed tasks" not in result.output


def test_move_id_shorthand_input(s1: str) -> None:
    t01 = add_subtask(s1, "Task A").task_id
    # s1 fixture is "s01"; shorthand "s1t9" should normalize to "s01t09"
    result = assert_invoke(app, ["move", t01, "--id", "s1t9"])
    assert f"{s1}t09" in result.output


def test_move_id_editor_opens_renamed_task(s1: str, run_editor: mock.Mock) -> None:
    add_subtask(s1, "Task A")
    t02 = add_subtask(s1, "Task B").task_id
    assert_invoke(app, ["move", t02, "--id", f"{s1}t09", "--editor"])
    opened_path: Path = run_editor.call_args[0][0]
    assert opened_path.exists()
    assert f"{s1}t09" in opened_path.name


def test_move_id_json_renames(s1: str, s2: str) -> None:
    t01 = add_subtask(s1, "Task A").task_id
    result = assert_invoke(app, ["--json-output", "move", t01, "--id", f"{s2}t01"])
    data = json.loads(result.output)
    assert "renames" in data
    assert data["renames"][0]["old_id"] == t01


# ---------------------------------------------------------------------------
# move clears `order` when the sibling set changes
# ---------------------------------------------------------------------------


def _stored_path(tasks_root: Path, task_id: str) -> Path:
    # the path `parse_task_file` accepts: a leaf is a flat `<ref>.md` file; a
    # parent with file-backed subtasks is an extended `<ref>/` directory
    for entry in tasks_root.rglob(f"{task_id}-*"):
        if entry.is_file() and entry.suffix == ".md":
            return entry
        if entry.is_dir() and (entry / "README.md").is_file():
            return entry
    raise AssertionError(f"No stored file for {task_id!r} under {tasks_root}")


def _fm_file(stored: Path) -> Path:
    return stored / "README.md" if stored.is_dir() else stored


def _has_stored_file(tasks_root: Path, task_id: str) -> bool:
    # inline subtasks live as bullets in the parent's file — no file of their own
    try:
        _stored_path(tasks_root, task_id)
        return True
    except AssertionError:
        return False


def _inject_order(tasks_root: Path, task_id: str, order: int) -> None:
    # emulate persisted `order:` storage (the `order` CLI lands in a later slice)
    path = _fm_file(_stored_path(tasks_root, task_id))
    content = path.read_text()
    new_content, count = re.subn(
        r"(?m)^(status: .*)$", rf"\1\norder: {order}", content, count=1
    )
    assert count == 1, f"No status line to anchor order after in {path}"
    path.write_text(new_content)


def test_move_ordered_subtask_to_new_parent_clears_order(
    s1: str, s2: str, tasks_root: Path
) -> None:
    t01 = add_subtask(s1, "Alpha", details="body here").task_id
    _inject_order(tasks_root, t01, 1000)

    assert_invoke(app, ["move", t01, "--parent", s2])

    moved = _stored_path(tasks_root, f"{s2}t01")
    assert moved.is_file() and moved.suffix == ".md"  # stayed a file, not inline
    assert parse_task_file(moved).task.order is None


def test_move_ordered_subtask_to_root_clears_order(s1: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Alpha", details="body here").task_id
    _inject_order(tasks_root, t01, 1000)

    assert_invoke(app, ["move", t01, "--root"])

    new_root = next(tasks_root.glob("s*-alpha.md"))
    assert parse_task_file(new_root).task.order is None


def test_move_id_to_different_parent_clears_order(
    s1: str, s2: str, tasks_root: Path
) -> None:
    t01 = add_subtask(s1, "Alpha", details="body here").task_id
    _inject_order(tasks_root, t01, 1000)

    assert_invoke(app, ["move", t01, "--id", f"{s2}t01"])

    moved = _stored_path(tasks_root, f"{s2}t01")
    assert parse_task_file(moved).task.order is None


def test_move_id_rename_same_parent_keeps_order(s1: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Alpha", details="body here").task_id
    _inject_order(tasks_root, t01, 1000)

    # pure rename within the same parent -- sibling set unchanged, order stays
    assert_invoke(app, ["move", t01, "--id", f"{s1}t05"])

    renamed = _stored_path(tasks_root, f"{s1}t05")
    assert parse_task_file(renamed).task.order == 1000


def test_move_id_rename_root_keeps_order(tasks_root: Path) -> None:
    s01 = create_task("Alpha").task_id
    _inject_order(tasks_root, s01, 1000)

    # pure rename of the root task
    assert_invoke(app, ["move", s01, "--id", "s05"])

    renamed = _stored_path(tasks_root, "s05")
    assert parse_task_file(renamed).task.order == 1000


def test_move_ordered_container_with_file_subtasks_stays_extended(
    s1: str, s2: str, tasks_root: Path
) -> None:
    t01 = add_subtask(s1, "Container", details="body here").task_id
    add_subtask(t01, "Child", details="child body")  # makes t01 an extended dir
    _inject_order(tasks_root, t01, 1000)

    assert_invoke(app, ["move", t01, "--parent", s2])

    moved = _stored_path(tasks_root, f"{s2}t01")
    assert moved.is_dir()  # stayed extended (directory), not downgraded
    assert parse_task_file(moved).task.order is None


def test_move_ordered_root_under_parent_clears_order(
    s1: str, s2: str, tasks_root: Path
) -> None:
    # a root task carries `order` relative to its root siblings; moving it under
    # a parent changes the sibling set, so the stale root rank must be dropped
    add_subtask(s1, "Child", details="child body")  # keeps s1 a file after move
    _inject_order(tasks_root, s1, 1000)

    assert_invoke(app, ["move", s1, "--parent", s2])

    moved = _stored_path(tasks_root, f"{s2}t01")
    assert parse_task_file(moved).task.order is None


def test_move_order_only_file_downgrades_to_inline(
    s1: str, s2: str, tasks_root: Path
) -> None:
    # a task that became a file *solely* to hold its order (no body, no children)
    # must downgrade back to an inline bullet once a plain move clears that order
    anchor = add_subtask(s1, "Anchor").task_id  # inline
    t02 = add_subtask(s1, "Alpha").task_id  # inline
    assert_invoke(app, ["order", anchor, t02])  # upgrades both to order-only files
    assert _has_stored_file(tasks_root, t02)  # precondition: now file-backed

    assert_invoke(app, ["move", t02, "--parent", s2])

    moved_id = f"{s2}t01"
    assert not _has_stored_file(tasks_root, moved_id)  # nothing left to keep it a file
    assert "Alpha" in assert_invoke(app, ["view", s2]).output  # shows as inline bullet
