import pytest

from tasker.base_types import TaskStatus
from tasker.exceptions import TaskHasSubtasksError
from tasker.mcp import finish_task, reset_task, start_task

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
    from tasker.mcp import view_task

    parent = view_task(story_id)
    assert parent.status == TaskStatus.IN_PROGRESS


def test_start_task_nonleaf_raises(story_id: str, leaf_ref: str) -> None:
    with pytest.raises(TaskHasSubtasksError):
        start_task(story_id)


# --- reset_task ---


def test_reset_task_returns_pending(leaf_ref: str) -> None:
    start_task(leaf_ref)
    result = reset_task(leaf_ref)
    assert result.status == TaskStatus.PENDING


def test_reset_already_pending_task(leaf_ref: str) -> None:
    result = reset_task(leaf_ref)
    assert result.status == TaskStatus.PENDING


def test_reset_task_nonleaf_raises(story_id: str, leaf_ref: str) -> None:
    with pytest.raises(TaskHasSubtasksError):
        reset_task(story_id)


# --- done_task ---


def test_done_task_returns_done(leaf_ref: str) -> None:
    result = finish_task(leaf_ref)
    assert result.status == TaskStatus.DONE


def test_done_task_persists_to_disk(story_id: str, leaf_ref: str) -> None:
    finish_task(leaf_ref)
    from tasker.mcp import view_task

    parent = view_task(story_id)
    assert parent.status == TaskStatus.DONE


def test_done_task_nonleaf_raises(story_id: str, leaf_ref: str) -> None:
    with pytest.raises(TaskHasSubtasksError):
        finish_task(story_id)


def test_done_task_force_closes_subtasks(story_id: str, leaf_ref: str) -> None:
    result = finish_task(story_id, force=True)
    assert result.status == TaskStatus.DONE
    assert result.subtasks is not None
    assert all(s.status == TaskStatus.DONE for s in result.subtasks)
