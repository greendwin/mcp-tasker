from unittest.mock import MagicMock

from tasker.cli._common import complete_task_ref

from .helpers import add_subtask, create_task


def _complete(incomplete: str = "") -> list[tuple[str, str]]:
    ctx = MagicMock()
    return complete_task_ref(ctx, [], incomplete)


def test_returns_empty_when_no_tasker_dir(project_root: object) -> None:
    # tasks_root fixture NOT used here so no tasker/ dir exists
    assert _complete() == []


def test_returns_task_ref(tasks_root: object) -> None:
    ref = create_task("Story one")
    completions = _complete()
    values = [v for v, _ in completions]
    assert ref.task_ref in values


def test_returns_task_title_as_help(tasks_root: object) -> None:
    create_task("Story one")
    completions = _complete()
    assert any(h == "Story one" for _, h in completions)


def test_returns_multiple_tasks(tasks_root: object) -> None:
    ref1 = create_task("Story one")
    ref2 = create_task("Story two")
    values = [v for v, _ in _complete()]
    assert ref1.task_ref in values
    assert ref2.task_ref in values


def test_filters_by_incomplete_prefix(tasks_root: object) -> None:
    ref1 = create_task("Story one")
    ref2 = create_task("Story two")
    values = [v for v, _ in _complete(ref1.task_id)]
    assert ref1.task_ref in values
    assert ref2.task_ref not in values


def test_returns_inline_subtasks(tasks_root: object) -> None:
    root = create_task("Story one")
    child = add_subtask(root.task_id, "Subtask one")
    completions = _complete()
    values = [v for v, _ in completions]
    assert child.task_ref in values


def test_filters_subtasks_by_incomplete_prefix(tasks_root: object) -> None:
    root = create_task("Story one")
    child = add_subtask(root.task_id, "Subtask one")
    values = [v for v, _ in _complete(child.task_id)]
    assert child.task_ref in values
    assert root.task_ref not in values


def test_empty_incomplete_returns_all(tasks_root: object) -> None:
    root = create_task("Story one")
    child = add_subtask(root.task_id, "Subtask one")
    values = [v for v, _ in _complete("")]
    assert root.task_ref in values
    assert child.task_ref in values
