import re
from pathlib import Path

from tasker.cli import app
from tasker.mcp import view_tasks

from .helpers import add_subtask, assert_invoke, create_task


def _set_order(tasks_root: Path, task_id: str, order: int) -> None:
    # inject an `order:` front-matter line into a task file, emulating the
    # persisted storage format so display surfaces can be tested black-box
    matches = [p for p in tasks_root.rglob(f"{task_id}-*.md")]
    assert matches, f"No task file found for {task_id!r} under {tasks_root}"
    assert len(matches) == 1, f"Ambiguous task file for {task_id!r}: {matches}"

    path = matches[0]
    content = path.read_text()
    new_content, count = re.subn(
        r"(?m)^(status: .*)$", rf"\1\norder: {order}", content, count=1
    )
    assert count == 1, f"No status line to anchor order after in {path}"
    path.write_text(new_content)


def _read_stored_task(tasks_root: Path, task_id: str) -> str:
    # a parent that has file-backed subtasks is stored as an extended task
    # directory (`<ref>/README.md`); a leaf is a flat `<ref>.md`
    candidates = []
    for entry in tasks_root.rglob(f"{task_id}-*"):
        if entry.is_file() and entry.suffix == ".md":
            candidates.append(entry)
        elif entry.is_dir() and (entry / "README.md").is_file():
            candidates.append(entry / "README.md")
    assert candidates, f"No stored task file found for {task_id!r} under {tasks_root}"
    assert len(candidates) == 1, f"Ambiguous stored file for {task_id!r}: {candidates}"
    return candidates[0].read_text()


def _positions(output: str, ids: list[str]) -> list[int]:
    positions = []
    for task_id in ids:
        idx = output.find(task_id)
        assert idx != -1, f"{task_id!r} not present in output:\n{output}"
        positions.append(idx)
    return positions


def _make_roots(count: int) -> list[str]:
    return [create_task(f"Story {i}").task_id for i in range(count)]


def _make_subtasks(parent_id: str, count: int) -> list[str]:
    return [
        add_subtask(parent_id, f"Sub {i}", details="body").task_id for i in range(count)
    ]


# --- Slice A: `list` orders root siblings by (order, id) ---


def test_list_orders_roots_ordered_lead_then_unset_by_id(tasks_root: Path) -> None:
    s01, s02, s03, s04 = _make_roots(4)
    _set_order(tasks_root, s03, 1000)
    _set_order(tasks_root, s04, 2000)

    result = assert_invoke(app, ["list"])

    positions = _positions(result.output, [s03, s04, s01, s02])
    assert positions == sorted(
        positions
    ), f"expected order {[s03, s04, s01, s02]}, got output:\n{result.output}"


def test_list_roots_all_unset_sort_by_id() -> None:
    s01, s02, s03, s04 = _make_roots(4)

    result = assert_invoke(app, ["list"])

    positions = _positions(result.output, [s01, s02, s03, s04])
    assert positions == sorted(
        positions
    ), f"expected id order, got output:\n{result.output}"


# --- Slice B: `view <parent>` orders subtasks by (order, id) ---


def test_view_orders_subtasks_ordered_lead_then_unset_by_id(tasks_root: Path) -> None:
    parent = create_task("Parent").task_id
    t01, t02, t03, t04 = _make_subtasks(parent, 4)
    _set_order(tasks_root, t03, 1000)
    _set_order(tasks_root, t04, 2000)

    result = assert_invoke(app, ["view", parent])

    positions = _positions(result.output, [t03, t04, t01, t02])
    assert positions == sorted(
        positions
    ), f"expected order {[t03, t04, t01, t02]}, got output:\n{result.output}"


def test_view_subtasks_duplicate_and_gapped_orders_tiebreak_by_id(
    tasks_root: Path,
) -> None:
    parent = create_task("Parent").task_id
    t01, t02, t03, t04 = _make_subtasks(parent, 4)
    _set_order(tasks_root, t01, 1000)
    _set_order(tasks_root, t03, 1000)  # duplicate order → tie-break by id
    _set_order(tasks_root, t04, 5000)  # gapped value
    # t02 left unset → sorts to the tail

    result = assert_invoke(app, ["view", parent])

    positions = _positions(result.output, [t01, t03, t04, t02])
    assert positions == sorted(
        positions
    ), f"expected order {[t01, t03, t04, t02]}, got output:\n{result.output}"


# --- Slice C: MCP `view_tasks` orders subtasks by (order, id) ---


def test_view_tasks_orders_subtasks_ordered_lead_then_unset_by_id(
    tasks_root: Path,
) -> None:
    parent = create_task("Parent").task_id
    t01, t02, t03, t04 = _make_subtasks(parent, 4)
    _set_order(tasks_root, t03, 1000)
    _set_order(tasks_root, t04, 2000)

    result = view_tasks([parent])

    positions = _positions(result, [t03, t04, t01, t02])
    assert positions == sorted(
        positions
    ), f"expected order {[t03, t04, t01, t02]}, got output:\n{result}"


# --- Slice D: display sort must not leak into stored bullet order (GREEN lock) ---


def test_display_sort_does_not_reorder_stored_subtasks(tasks_root: Path) -> None:
    parent = create_task("Parent").task_id
    t01, t02, t03, t04 = _make_subtasks(parent, 4)
    # make display order (t03, t04, t01, t02) differ from storage order
    _set_order(tasks_root, t03, 1000)
    _set_order(tasks_root, t04, 2000)

    # a display command must not rewrite the parent's stored `## Subtasks` bullets
    assert_invoke(app, ["view", parent])

    stored = _read_stored_task(tasks_root, parent)
    positions = _positions(stored, [t01, t02, t03, t04])
    assert positions == sorted(
        positions
    ), f"stored bullet order changed; expected {[t01, t02, t03, t04]}, got:\n{stored}"


# --- Slice E: `list` tree orders subtasks by (order, id) ---


def test_list_tree_orders_subtasks_ordered_lead_then_unset_by_id(
    tasks_root: Path,
) -> None:
    parent = create_task("Parent").task_id
    t01, t02, t03, t04 = _make_subtasks(parent, 4)
    _set_order(tasks_root, t03, 1000)
    _set_order(tasks_root, t04, 2000)

    result = assert_invoke(app, ["list"])

    positions = _positions(result.output, [t03, t04, t01, t02])
    assert positions == sorted(
        positions
    ), f"expected order {[t03, t04, t01, t02]}, got output:\n{result.output}"


def test_list_tree_subtasks_all_unset_sort_by_id() -> None:
    parent = create_task("Parent").task_id
    t01, t02, t03, t04 = _make_subtasks(parent, 4)

    result = assert_invoke(app, ["list"])

    positions = _positions(result.output, [t01, t02, t03, t04])
    assert positions == sorted(
        positions
    ), f"expected id order, got output:\n{result.output}"
