from pathlib import Path
from typing import Any, Protocol

import pytest

from tasker.base_types import Task, TaskStatus
from tasker.cli import app
from tasker.exceptions import TaskHasSubtasksError
from tasker.mcp import (
    MutationResult,
    cancel_task,
    edit_task,
    finish_task,
    reset_task,
    review_task,
    start_task,
)
from tasker.mcp._common import get_repo
from tasker.resolve import resolve_ref

from .helpers import add_subtask, assert_invoke, create_task


def _load_task(ref: str) -> Task:
    return resolve_ref(get_repo(), ref).task


def _all_subtask_ids(task: Task) -> list[str]:
    return [child.id for child in task.subtasks]


class _ForceMutator(Protocol):
    def __call__(self, task_ref: str, force: bool = ...) -> MutationResult: ...


@pytest.fixture()
def story_id() -> str:
    return create_task("My story").task_id


@pytest.fixture()
def leaf_ref(story_id: str) -> str:
    return add_subtask(story_id, "Leaf task").task_ref


# --- start_task ---


def test_start_task_returns_in_progress(leaf_ref: str) -> None:
    result = start_task(leaf_ref)
    assert result.status == TaskStatus.IN_PROGRESS


def test_start_task_returns_mutation_result(leaf_ref: str) -> None:
    result = start_task(leaf_ref)
    assert isinstance(result, MutationResult)


def test_start_task_persists_to_disk(story_id: str, leaf_ref: str) -> None:
    start_task(leaf_ref)
    # verify by viewing the parent — its status should update to in-progress
    parent = _load_task(story_id)
    assert parent.status == TaskStatus.IN_PROGRESS


def test_start_task_nonleaf_raises(story_id: str, leaf_ref: str) -> None:
    with pytest.raises(TaskHasSubtasksError):
        start_task(story_id)


# --- review_task ---


def test_review_task_returns_in_review(leaf_ref: str) -> None:
    result = review_task(leaf_ref)
    assert result.status == TaskStatus.IN_REVIEW


def test_review_task_persists_to_disk(story_id: str, leaf_ref: str) -> None:
    review_task(leaf_ref)
    parent = _load_task(story_id)
    assert parent.status == TaskStatus.IN_PROGRESS


def test_review_task_nonleaf_raises(story_id: str, leaf_ref: str) -> None:
    with pytest.raises(TaskHasSubtasksError):
        review_task(story_id)


def test_review_task_idempotent(leaf_ref: str) -> None:
    review_task(leaf_ref)
    result = review_task(leaf_ref)
    assert result.status == TaskStatus.IN_REVIEW


def test_done_after_review(leaf_ref: str) -> None:
    review_task(leaf_ref)
    result = finish_task(leaf_ref)
    assert result.status == TaskStatus.DONE


# --- reset_task ---


def test_reset_task_returns_pending(leaf_ref: str) -> None:
    start_task(leaf_ref)
    result = reset_task(leaf_ref)
    assert result.status == TaskStatus.PENDING


def test_reset_already_pending_task(leaf_ref: str) -> None:
    result = reset_task(leaf_ref)
    assert result.status == TaskStatus.PENDING


def test_reset_task_nonleaf_raises(story_id: str, leaf_ref: str) -> None:
    start_task(leaf_ref)

    with pytest.raises(TaskHasSubtasksError):
        reset_task(story_id)


def test_reset_pending_nonleaf_is_ok(story_id: str, leaf_ref: str) -> None:
    ti = reset_task(story_id)
    assert ti.status == "pending"
    assert ti.affected == []


@pytest.mark.parametrize(
    "mutator, expected_status",
    [
        (reset_task, "pending"),
        (finish_task, "done"),
        (cancel_task, "cancelled"),
    ],
)
def test_force_mutators_apply_to_subtasks(
    story_id: str,
    leaf_ref: str,
    mutator: _ForceMutator,
    expected_status: str,
) -> None:
    mutator(story_id, force=True)
    all_ids = _all_subtask_ids(_load_task(story_id))
    assert len(all_ids) > 0
    for cid in all_ids:
        assert _load_task(cid).status == TaskStatus(expected_status)


# --- affected (cascade reporting) ---


@pytest.mark.parametrize("mutator", [reset_task, finish_task, cancel_task])
def test_force_reports_cascaded_children(
    story_id: str, leaf_ref: str, mutator: _ForceMutator
) -> None:
    start_task(leaf_ref)
    child_ids = _all_subtask_ids(_load_task(story_id))
    result = mutator(story_id, force=True)
    assert set(result.affected) == set(child_ids)
    assert story_id not in result.affected


def test_finish_force_reports_recursive_descendants(story_id: str) -> None:
    mid_id = add_subtask(story_id, "Mid subtask").task_id
    grandchild_id = add_subtask(mid_id, "Leaf grandchild").task_id

    result = finish_task(story_id, force=True)

    assert set(result.affected) == {mid_id, grandchild_id}
    assert story_id not in result.affected


def test_reset_force_reports_recursive_descendants(story_id: str) -> None:
    mid_id = add_subtask(story_id, "Mid subtask").task_id
    grandchild_id = add_subtask(mid_id, "Leaf grandchild").task_id
    start_task(grandchild_id)

    result = reset_task(story_id, force=True)

    assert set(result.affected) == {mid_id, grandchild_id}
    assert story_id not in result.affected


def test_finish_force_skips_already_closed_child(story_id: str) -> None:
    child_a = add_subtask(story_id, "Child A").task_id
    child_b = add_subtask(story_id, "Child B").task_id
    finish_task(child_a)

    result = finish_task(story_id, force=True)

    assert result.affected == [child_b]


def test_reset_force_skips_already_pending_child(story_id: str) -> None:
    add_subtask(story_id, "Child A")
    child_b = add_subtask(story_id, "Child B").task_id
    start_task(child_b)

    result = reset_task(story_id, force=True)

    assert result.affected == [child_b]


def test_finish_leaf_has_no_affected(leaf_ref: str) -> None:
    result = finish_task(leaf_ref)
    assert result.affected == []


# --- serialized ack omits empty affected ---


def _serialize(result: MutationResult) -> dict[str, Any]:
    # mirrors how FastMCP emits the tool's structured content to the caller
    return result.model_dump(mode="json", by_alias=True)


def test_start_task_ack_omits_empty_affected(leaf_ref: str) -> None:
    payload = _serialize(start_task(leaf_ref))
    assert "affected" not in payload


def test_edit_task_ack_omits_empty_affected(leaf_ref: str) -> None:
    payload = _serialize(edit_task(leaf_ref, title="Renamed"))
    assert "affected" not in payload


def test_finish_noncascade_ack_omits_empty_affected(leaf_ref: str) -> None:
    payload = _serialize(finish_task(leaf_ref))
    assert "affected" not in payload


def test_finish_cascade_ack_includes_affected(story_id: str, leaf_ref: str) -> None:
    child_ids = _all_subtask_ids(_load_task(story_id))
    payload = _serialize(finish_task(story_id, force=True))
    assert set(payload["affected"]) == set(child_ids)


def test_force_with_nothing_to_cascade_has_no_affected(leaf_ref: str) -> None:
    result = finish_task(leaf_ref, force=True)
    assert result.affected == []


def test_force_false_on_leaf_has_no_affected(leaf_ref: str) -> None:
    result = finish_task(leaf_ref, force=False)
    assert result.affected == []


# --- done_task ---


def test_done_task_returns_done(leaf_ref: str) -> None:
    result = finish_task(leaf_ref)
    assert result.status == TaskStatus.DONE


def test_done_task_persists_to_disk(story_id: str, leaf_ref: str) -> None:
    finish_task(leaf_ref)

    parent = _load_task(story_id)
    assert parent.status == TaskStatus.DONE


def test_done_task_nonleaf_raises(story_id: str, leaf_ref: str) -> None:
    with pytest.raises(TaskHasSubtasksError):
        finish_task(story_id)


# --- cancel_task ---


def test_cancel_task_returns_cancelled(leaf_ref: str) -> None:
    result = cancel_task(leaf_ref)
    assert result.status == TaskStatus.CANCELLED


def test_cancel_task_already_cancelled(leaf_ref: str) -> None:
    cancel_task(leaf_ref)
    result = cancel_task(leaf_ref)
    assert result.status == TaskStatus.CANCELLED
    assert result.affected == []


# --- .closed history via MCP ---


def test_mcp_finish_task_appends_to_closed(leaf_ref: str, tasks_root: Path) -> None:
    result = finish_task(leaf_ref)
    stored = (tasks_root / ".closed").read_text().splitlines()
    assert result.id in stored


def test_mcp_cancel_task_appends_to_closed(leaf_ref: str, tasks_root: Path) -> None:
    result = cancel_task(leaf_ref)
    stored = (tasks_root / ".closed").read_text().splitlines()
    assert result.id in stored


def test_mcp_finish_task_force_excludes_forced_children(
    story_id: str, leaf_ref: str, tasks_root: Path
) -> None:
    finish_task(story_id, force=True)
    stored = (tasks_root / ".closed").read_text().splitlines()
    assert story_id in stored
    parent = _load_task(story_id)
    child_ids = _all_subtask_ids(parent)
    assert child_ids  # sanity
    for cid in child_ids:
        assert cid not in stored


def test_mcp_cancel_task_force_excludes_forced_children(
    story_id: str, leaf_ref: str, tasks_root: Path
) -> None:
    parent = _load_task(story_id)
    child_ids = _all_subtask_ids(parent)
    assert child_ids  # sanity
    cancel_task(story_id, force=True)
    stored = (tasks_root / ".closed").read_text().splitlines()
    assert story_id in stored
    for cid in child_ids:
        assert cid not in stored


# --- shortcut resolution ---


def test_start_task_resolves_t_letter_shortcut() -> None:
    s1 = create_task("Story one").task_id
    leaf = add_subtask(s1, "Leaf").task_ref
    assert_invoke(app, ["todo", leaf])
    result = start_task("ta")
    assert result.id == leaf
    assert result.status == TaskStatus.IN_PROGRESS


def test_finish_task_resolves_t_letter_shortcut() -> None:
    s1 = create_task("Story one").task_id
    leaf = add_subtask(s1, "Leaf").task_ref
    assert_invoke(app, ["todo", leaf])
    result = finish_task("ta")
    assert result.id == leaf
    assert result.status == TaskStatus.DONE


def test_review_task_resolves_t_letter_shortcut() -> None:
    s1 = create_task("Story one").task_id
    leaf = add_subtask(s1, "Leaf").task_ref
    assert_invoke(app, ["todo", leaf])
    result = review_task("ta")
    assert result.id == leaf
    assert result.status == TaskStatus.IN_REVIEW


def test_reset_task_resolves_t_letter_shortcut() -> None:
    s1 = create_task("Story one").task_id
    leaf = add_subtask(s1, "Leaf").task_ref
    assert_invoke(app, ["todo", leaf])
    result = reset_task("ta")
    assert result.id == leaf


def test_cancel_task_resolves_t_letter_shortcut() -> None:
    s1 = create_task("Story one").task_id
    leaf = add_subtask(s1, "Leaf").task_ref
    assert_invoke(app, ["todo", leaf])
    result = cancel_task("ta")
    assert result.id == leaf


def test_edit_task_resolves_t_letter_shortcut() -> None:
    s1 = create_task("Story one").task_id
    leaf = add_subtask(s1, "Leaf").task_ref
    assert_invoke(app, ["todo", leaf])
    result = edit_task("ta", title="Renamed leaf")
    assert result.id == leaf
