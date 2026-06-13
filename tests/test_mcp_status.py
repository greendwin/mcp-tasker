from pathlib import Path
from typing import Protocol

import pytest

from tasker.base_types import TaskStatus
from tasker.cli import app
from tasker.exceptions import TaskHasSubtasksError
from tasker.mcp import (
    TaskInfo,
    TaskPreview,
    cancel_task,
    finish_task,
    reset_task,
    resource_task,
    review_task,
    start_task,
    view_tasks,
)
from tasker.mcp._render import TASK_BLOCK_SEPARATOR

from .helpers import add_subtask, assert_invoke, create_task


def _all_subtask_ids(info: TaskInfo) -> list[str]:
    return [tid for ids in info.subtasks.values() for tid in ids]


class _ForceMutator(Protocol):
    def __call__(self, task_ref: str, force: bool = ...) -> TaskPreview: ...


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


def test_start_task_persists_to_disk(story_id: str, leaf_ref: str) -> None:
    start_task(leaf_ref)
    # verify by viewing the parent — its status should update to in-progress
    parent = resource_task(story_id)
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
    parent = resource_task(story_id)
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
    full_info = resource_task(story_id)
    all_ids = _all_subtask_ids(full_info)
    assert len(all_ids) > 0
    markdown = view_tasks(all_ids)
    blocks = markdown.split(TASK_BLOCK_SEPARATOR)
    assert all(f"status: {expected_status}" in block for block in blocks)


# --- done_task ---


def test_done_task_returns_done(leaf_ref: str) -> None:
    result = finish_task(leaf_ref)
    assert result.status == TaskStatus.DONE


def test_done_task_persists_to_disk(story_id: str, leaf_ref: str) -> None:
    finish_task(leaf_ref)

    parent = resource_task(story_id)
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
    full = resource_task(story_id)
    child_ids = _all_subtask_ids(full)
    assert child_ids  # sanity
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
