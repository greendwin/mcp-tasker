import inspect
from pathlib import Path
from typing import Any

import pytest

import tasker.mcp as mcp_pkg
from tasker.base_types import Task
from tasker.cli import app
from tasker.exceptions import TaskerError
from tasker.mcp import MutationResult, order_tasks
from tasker.mcp._common import get_repo
from tasker.resolve import load_recent_task, resolve_ref

from .helpers import add_subtask, assert_invoke, create_task


def _load_task(ref: str) -> Task:
    return resolve_ref(get_repo(), ref).task


def _stored_path(tasks_root: Path, task_id: str) -> Path | None:
    for entry in tasks_root.rglob(f"{task_id}-*"):
        if entry.is_file() and entry.suffix == ".md":
            return entry
        if entry.is_dir() and (entry / "README.md").is_file():
            return entry
    return None


def _has_stored_file(tasks_root: Path, task_id: str) -> bool:
    return _stored_path(tasks_root, task_id) is not None


def _subtask_order(parent_ref: str) -> list[str]:
    # child ids in display order (render_task_markdown sorts by (order, id))
    return [child.id for child in sorted(_load_task(parent_ref).subtasks)]


def _serialize(result: MutationResult) -> dict[str, Any]:
    return result.model_dump(mode="json", by_alias=True)


@pytest.fixture()
def story_id() -> str:
    return create_task("My story").task_id


# --- Slice A: base anchor-first grouping ---


def test_order_tasks_groups_after_anchor(story_id: str) -> None:
    t01 = add_subtask(story_id, "One").task_id
    t02 = add_subtask(story_id, "Two").task_id
    t03 = add_subtask(story_id, "Three").task_id
    t04 = add_subtask(story_id, "Four").task_id  # unset tail, untouched

    order_tasks([t01, t03, t02])

    order = _subtask_order(story_id)
    # anchor first, then moved in argument order, unset tail last
    assert order.index(t01) < order.index(t03) < order.index(t02) < order.index(t04)


def test_order_tasks_rejects_single_ref(story_id: str) -> None:
    t01 = add_subtask(story_id, "One").task_id
    add_subtask(story_id, "Two")

    # MCP is stricter than CLI base: a lone ref carries no ordering intent
    with pytest.raises(TaskerError):
        order_tasks([t01])


def test_order_tasks_upgrades_inline_sibling_to_file(
    story_id: str, tasks_root: Path
) -> None:
    t01 = add_subtask(story_id, "One").task_id  # inline bullet, no file
    t02 = add_subtask(story_id, "Two").task_id
    assert not _has_stored_file(tasks_root, t02)  # sanity: inline before

    order_tasks([t01, t02])

    assert _has_stored_file(tasks_root, t02)


# --- Slice B: concise ack ---


def test_order_tasks_returns_anchor_mutation_result(story_id: str) -> None:
    t01 = add_subtask(story_id, "One").task_id
    t02 = add_subtask(story_id, "Two").task_id

    result = order_tasks([t01, t02])

    assert isinstance(result, MutationResult)
    assert result.id == t01
    assert result.status == _load_task(t01).status


def test_order_tasks_ack_omits_affected(story_id: str) -> None:
    t01 = add_subtask(story_id, "One").task_id
    t02 = add_subtask(story_id, "Two").task_id

    payload = _serialize(order_tasks([t01, t02]))

    assert "affected" not in payload


def test_order_tasks_does_not_touch_recent(story_id: str) -> None:
    t01 = add_subtask(story_id, "One").task_id
    t02 = add_subtask(story_id, "Two").task_id
    other = create_task("Other story").task_id
    assert_invoke(app, ["todo", other])  # user parks recent here

    order_tasks([t01, t02])

    # MCP mutations never move .recent -- it is a human-interaction affordance
    recent = load_recent_task(get_repo())
    assert recent is not None
    assert recent.id == other


# --- Slice C: strict same-parent guard ---


def test_order_tasks_rejects_cross_parent_ref() -> None:
    s1 = create_task("Story one").task_id
    s2 = create_task("Story two").task_id
    a = add_subtask(s1, "Under one").task_id
    b = add_subtask(s2, "Under two").task_id

    with pytest.raises(TaskerError):
        order_tasks([a, b])


def test_order_tasks_cross_parent_error_leaves_state_unchanged() -> None:
    s1 = create_task("Story one").task_id
    s2 = create_task("Story two").task_id
    a = add_subtask(s1, "Under one").task_id
    b = add_subtask(s2, "Under two").task_id

    with pytest.raises(TaskerError):
        order_tasks([a, b])

    # nothing reparented, nothing ordered
    assert _load_task(b).id == b
    assert _subtask_order(s2) == [b]
    assert _load_task(a).order is None
    assert _load_task(b).order is None


# --- Slice D: minimal surface & wiring ---


def test_order_tasks_exported_from_package() -> None:
    assert "order_tasks" in mcp_pkg.__all__
    assert mcp_pkg.order_tasks is order_tasks


def test_order_tasks_signature_exposes_only_task_refs() -> None:
    params = list(inspect.signature(order_tasks).parameters)
    assert params == ["task_refs"]


def test_order_tasks_resolves_shortcut_ref(story_id: str) -> None:
    a = add_subtask(story_id, "One").task_id
    b = add_subtask(story_id, "Two").task_id
    assert_invoke(app, ["todo", a])

    result = order_tasks(["ta", b])

    assert result.id == a


# --- Slice E: empty input rejected ---


def test_order_tasks_rejects_empty_list() -> None:
    with pytest.raises(TaskerError):
        order_tasks([])
