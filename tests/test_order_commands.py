from pathlib import Path

import pytest

from tasker.cli import app
from tasker.parse import parse_task_file

from .helpers import add_subtask, assert_invoke, create_task


@pytest.fixture()
def story() -> str:
    return create_task("Story").task_id


def _stored_path(tasks_root: Path, task_id: str) -> Path:
    # a leaf is a flat `<ref>.md` file; a parent with file-backed subtasks is an
    # extended `<ref>/` directory (rglob reaches nested subtask files)
    for entry in tasks_root.rglob(f"{task_id}-*"):
        if entry.is_file() and entry.suffix == ".md":
            return entry
        if entry.is_dir() and (entry / "README.md").is_file():
            return entry
    raise AssertionError(f"No stored file for {task_id!r} under {tasks_root}")


def _fm_file(stored: Path) -> Path:
    return stored / "README.md" if stored.is_dir() else stored


def _order_of(tasks_root: Path, task_id: str) -> int | None:
    return parse_task_file(_fm_file(_stored_path(tasks_root, task_id))).task.order


def _has_stored_file(tasks_root: Path, task_id: str) -> bool:
    # inline subtasks live as bullets in the parent's file — no file of their own
    try:
        _stored_path(tasks_root, task_id)
        return True
    except AssertionError:
        return False


# --- Slice A: group moved at anchor, in argument order ---


def test_order_groups_moved_contiguous_in_argument_order(
    story: str, tasks_root: Path
) -> None:
    t01 = add_subtask(story, "One").task_id
    t02 = add_subtask(story, "Two").task_id
    t03 = add_subtask(story, "Three").task_id
    add_subtask(story, "Four")  # unset tail, untouched

    assert_invoke(app, ["order", t01, t03, t02])

    a = _order_of(tasks_root, t01)
    b = _order_of(tasks_root, t03)
    c = _order_of(tasks_root, t02)
    assert a is not None and b is not None and c is not None
    # anchor first, then moved in argument order (t03 before t02)
    assert a < b < c


def test_order_pulls_moved_from_prior_ordered_position(
    story: str, tasks_root: Path
) -> None:
    t01 = add_subtask(story, "One").task_id
    t02 = add_subtask(story, "Two").task_id
    t03 = add_subtask(story, "Three").task_id

    # establish an initial order, then pull t03 up to sit right after t01
    assert_invoke(app, ["order", t01, t02, t03])
    assert_invoke(app, ["order", t01, t03])

    a = _order_of(tasks_root, t01)
    moved = _order_of(tasks_root, t03)
    other = _order_of(tasks_root, t02)
    assert a is not None and moved is not None and other is not None
    # t03 now leads t02 (pulled from behind it)
    assert a < moved < other


# --- Slice B: inline moved task auto-upgrades to a file ---


def test_order_upgrades_inline_moved_to_file(story: str, tasks_root: Path) -> None:
    t01 = add_subtask(story, "One").task_id
    t02 = add_subtask(story, "Two").task_id  # inline (no --details)

    assert not _has_stored_file(tasks_root, t02)  # precondition: inline

    assert_invoke(app, ["order", t01, t02])

    stored = _stored_path(tasks_root, t02)
    assert stored.is_file() and stored.suffix == ".md"
    assert parse_task_file(stored).task.order is not None


# --- Slice C: sparse write — untouched siblings unmodified ---


def test_order_leaves_untouched_sibling_bytes_unchanged(
    story: str, tasks_root: Path
) -> None:
    t01 = add_subtask(story, "One").task_id
    t02 = add_subtask(story, "Two").task_id
    keep = add_subtask(story, "Keep", details="untouched body").task_id

    keep_path = _fm_file(_stored_path(tasks_root, keep))
    before = keep_path.read_bytes()

    assert_invoke(app, ["order", t01, t02])

    # unreferenced, unset-tail sibling is dirty-checked out — not rewritten
    assert _fm_file(_stored_path(tasks_root, keep)).read_bytes() == before


# --- Slice D: non-sibling refs error clearly ---


def test_order_cross_parent_refs_errors() -> None:
    s1 = create_task("Story one").task_id
    s2 = create_task("Story two").task_id
    a = add_subtask(s1, "A").task_id
    b = add_subtask(s2, "B").task_id

    result = assert_invoke(app, ["order", a, b], expect_error=True)

    assert "sibling" in result.output.lower() or "parent" in result.output.lower()


# --- Slice E: single-arg is a true no-op with a warning ---


def test_order_single_arg_is_noop_with_warning(story: str, tasks_root: Path) -> None:
    t01 = add_subtask(story, "One").task_id
    add_subtask(story, "Two")

    story_path = _fm_file(_stored_path(tasks_root, story))
    before = story_path.read_bytes()

    result = assert_invoke(app, ["order", t01])

    # nothing on disk changed; the anchor did not gain an order
    assert _fm_file(_stored_path(tasks_root, story)).read_bytes() == before
    assert "at least one" in result.output.lower()
