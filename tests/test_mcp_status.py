import pytest

from tasker.base_types import TaskStatus
from tasker.exceptions import TaskHasSubtasksError
from tasker.mcp import (
    cancel_task,
    finish_task,
    reset_task,
    resource_task,
    review_task,
    start_task,
    view_tasks,
)

from .helpers import add_subtask, create_task


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


def test_reset_task_force_resets_subtasks(story_id: str, leaf_ref: str) -> None:
    start_task(leaf_ref)
    result = reset_task(story_id, force=True)
    assert result.status == TaskStatus.PENDING
    all_ids = [tid for ids in result.subtasks.values() for tid in ids]
    assert len(all_ids) > 0
    subtask_infos = view_tasks(all_ids)
    assert all(s.status == TaskStatus.PENDING for s in subtask_infos)


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


def test_done_task_force_closes_subtasks(story_id: str, leaf_ref: str) -> None:
    result = finish_task(story_id, force=True)
    assert result.status == TaskStatus.DONE
    all_ids = [tid for ids in result.subtasks.values() for tid in ids]
    assert len(all_ids) > 0
    subtask_infos = view_tasks(all_ids)
    assert all(s.status == TaskStatus.DONE for s in subtask_infos)


# --- cancel_task ---


def test_cancel_task_returns_cancelled(leaf_ref: str) -> None:
    result = cancel_task(leaf_ref)
    assert result.status == TaskStatus.CANCELLED


def test_cancel_task_force_cancels_subtasks(story_id: str, leaf_ref: str) -> None:
    result = cancel_task(story_id, force=True)
    assert result.status == TaskStatus.CANCELLED
    all_ids = [tid for ids in result.subtasks.values() for tid in ids]
    subtask_infos = view_tasks(all_ids)
    assert all(s.status == TaskStatus.CANCELLED for s in subtask_infos)


def test_cancel_task_already_cancelled(leaf_ref: str) -> None:
    cancel_task(leaf_ref)
    result = cancel_task(leaf_ref)
    assert result.status == TaskStatus.CANCELLED
