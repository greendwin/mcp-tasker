from pathlib import Path

import pytest

from tasker.cli import app
from tasker.layout import TASKER_DIR, init_tasker_dir

from .helpers import add_subtask, assert_invoke, create_task


def _read_recent(tasks_root: Path) -> str | None:
    path = tasks_root / ".recent"
    if not path.exists():
        return None
    text = path.read_text().strip()
    return text or None


@pytest.fixture()
def s1() -> str:
    return create_task("Story one").task_id


# ---------------------------------------------------------------------------
# Store last target task on commands
# ---------------------------------------------------------------------------


def test_new_stores_recent(tasks_root: Path) -> None:
    ref = create_task("Brand new story")
    assert _read_recent(tasks_root) == ref.task_id


def test_add_stores_recent(s1: str, tasks_root: Path) -> None:
    add_subtask(s1, "Child task")
    assert _read_recent(tasks_root) == s1


def test_edit_stores_recent(s1: str, tasks_root: Path) -> None:
    assert_invoke(app, ["edit", s1, "--title", "Updated title"])
    assert _read_recent(tasks_root) == s1


def test_move_stores_recent(tasks_root: Path) -> None:
    s1 = create_task("Story A").task_id
    s2 = create_task("Story B").task_id
    t01 = add_subtask(s1, "Task to move", details="d").task_id

    assert_invoke(app, ["move", t01, "--parent", s2])
    # after move, task ID changes (s01t01 -> s02t01)
    recent = _read_recent(tasks_root)
    assert recent is not None
    assert recent.startswith(s2)


def test_unarchive_stores_recent(tasks_root: Path) -> None:
    s1 = create_task("Archivable story").task_id
    assert_invoke(app, ["done", s1])
    assert_invoke(app, ["archive", s1])

    assert_invoke(app, ["unarchive", s1])
    assert _read_recent(tasks_root) == s1


def test_start_stores_recent(s1: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Task A").task_id
    assert_invoke(app, ["start", t01])
    assert _read_recent(tasks_root) == t01


def test_done_stores_recent(s1: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Task A").task_id
    assert_invoke(app, ["done", t01])
    assert _read_recent(tasks_root) == t01


def test_cancel_stores_recent(s1: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Task A").task_id
    assert_invoke(app, ["cancel", t01])
    assert _read_recent(tasks_root) == t01


def test_reset_stores_recent(s1: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Task A").task_id
    assert_invoke(app, ["start", t01])
    assert_invoke(app, ["reset", t01])
    assert _read_recent(tasks_root) == t01


# ---------------------------------------------------------------------------
# .recent file and .gitignore
# ---------------------------------------------------------------------------


def test_recent_written_to_file(tasks_root: Path) -> None:
    ref = create_task("Test story")
    recent_file = tasks_root / ".recent"
    assert recent_file.exists()
    assert recent_file.read_text().strip() == ref.task_id


def test_gitignore_created_by_init(project_root: Path) -> None:
    init_tasker_dir(project_root)

    gitignore = project_root / TASKER_DIR / ".gitignore"
    assert gitignore.exists()
    assert ".recent" in gitignore.read_text().splitlines()


def test_gitignore_created_by_auto_init(project_root: Path) -> None:
    # auto-init happens when discover finds .git but no tasker/
    create_task("Test story")

    gitignore = project_root / TASKER_DIR / ".gitignore"
    assert gitignore.exists()
    assert ".recent" in gitignore.read_text().splitlines()


def test_load_recent_returns_none_when_no_file(tasks_root: Path) -> None:
    assert _read_recent(tasks_root) is None


# ---------------------------------------------------------------------------
# Resolve 'q' reference
# ---------------------------------------------------------------------------


def test_q_resolves_to_recent_task(s1: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Task A").task_id
    assert_invoke(app, ["start", t01])  # sets recent to t01

    # 'q' should resolve to t01 — use edit which requires valid task ref
    assert_invoke(app, ["edit", "q", "--title", "Updated via q"])


def test_q_errors_when_no_recent(tasks_root: Path) -> None:
    assert_invoke(app, ["edit", "q", "--title", "nope"], expect_error=True)


def test_q_does_not_update_recent(s1: str, tasks_root: Path) -> None:
    add_subtask(s1, "Task A")
    t02 = add_subtask(s1, "Task B").task_id
    assert_invoke(app, ["start", t02])  # sets recent to t02

    # 'q' is not a direct link — recent should stay as t02
    assert_invoke(app, ["edit", "q", "--title", "Edited via q"])
    assert _read_recent(tasks_root) == t02


# ---------------------------------------------------------------------------
# Resolve 'p' reference
# ---------------------------------------------------------------------------


def test_p_resolves_to_parent_of_recent(s1: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Task A").task_id
    assert_invoke(app, ["start", t01])  # recent = s01t01

    # 'p' should resolve to s01 (parent of s01t01)
    assert_invoke(app, ["edit", "p", "--title", "Parent edited via p"])


def test_p_resolves_to_parent_of_nested_task(tasks_root: Path) -> None:
    s1 = create_task("Story one").task_id
    t01 = add_subtask(s1, "Task A", details="d").task_id
    t0101 = add_subtask(t01, "Subtask A1").task_id
    assert_invoke(app, ["start", t0101])  # recent = s01t0101

    # 'p' should resolve to s01t01 (parent of s01t0101)
    assert_invoke(app, ["edit", "p", "--title", "Mid-level edited via p"])


def test_p_on_root_task_resolves_to_itself(tasks_root: Path) -> None:
    s1 = create_task("Story one").task_id
    assert_invoke(app, ["edit", s1, "--title", "Set recent"])  # recent = s01

    # 'p' of root task is the root task itself
    assert_invoke(app, ["edit", "p", "--title", "Root edited via p"])


def test_p_errors_when_no_recent(tasks_root: Path) -> None:
    assert_invoke(app, ["edit", "p", "--title", "nope"], expect_error=True)


def test_p_does_not_update_recent(s1: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Task A").task_id
    assert_invoke(app, ["start", t01])  # recent = s01t01

    # 'p' is a shortcut — recent must stay as t01
    assert_invoke(app, ["edit", "p", "--title", "Parent edited via p"])
    assert _read_recent(tasks_root) == t01


# ---------------------------------------------------------------------------
# Resolve 'pNN' / 'pNNNN...' reference
# ---------------------------------------------------------------------------


def test_p_digits_resolves_sibling(s1: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Task A").task_id
    add_subtask(s1, "Task B")
    assert_invoke(app, ["start", t01])  # recent = s01t01

    # p02 -> parent(s01t01)=s01 + t02 -> s01t02
    assert_invoke(app, ["edit", "p02", "--title", "Sibling edited via p02"])


def test_p_digits_resolves_from_nested(tasks_root: Path) -> None:
    s1 = create_task("Story one").task_id
    t01 = add_subtask(s1, "Task A", details="d").task_id
    t0101 = add_subtask(t01, "Sub A1").task_id
    add_subtask(t01, "Sub A2")
    assert_invoke(app, ["start", t0101])  # recent = s01t0101

    # p02 -> parent(s01t0101)=s01t01 + t02 -> s01t0102
    assert_invoke(app, ["edit", "p02", "--title", "Cousin edited via p02"])


def test_p_deep_digits_resolves_nested_path(tasks_root: Path) -> None:
    s1 = create_task("Story one").task_id
    t01 = add_subtask(s1, "Task A", details="d").task_id
    add_subtask(t01, "Sub A1")
    assert_invoke(app, ["edit", t01, "--title", "Set recent"])  # recent = s01t01

    # p0101 -> parent(s01t01)=s01 + t0101 -> s01t0101
    assert_invoke(app, ["edit", "p0101", "--title", "Deep edited via p0101"])


def test_p_digits_errors_when_no_recent(tasks_root: Path) -> None:
    assert_invoke(app, ["edit", "p01", "--title", "nope"], expect_error=True)


def test_p_digits_errors_for_nonexistent_sibling(s1: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Task A").task_id
    assert_invoke(app, ["start", t01])  # recent = s01t01

    # p99 -> s01t99 which doesn't exist
    assert_invoke(app, ["edit", "p99", "--title", "nope"], expect_error=True)


# ---------------------------------------------------------------------------
# Resolve 'pp' reference
# ---------------------------------------------------------------------------


def test_pp_resolves_to_grandparent(tasks_root: Path) -> None:
    s1 = create_task("Story one").task_id
    t01 = add_subtask(s1, "Task A", details="d").task_id
    t0101 = add_subtask(t01, "Sub A1").task_id
    assert_invoke(app, ["start", t0101])  # recent = s01t0101

    # pp -> parent(s01t0101)=s01t01 -> parent(s01t01)=s01
    assert_invoke(app, ["edit", "pp", "--title", "Grandparent edited via pp"])


def test_pp_on_level1_resolves_to_root(s1: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Task A").task_id
    assert_invoke(app, ["start", t01])  # recent = s01t01

    # pp -> parent(s01t01)=s01 -> parent(s01)=s01
    assert_invoke(app, ["edit", "pp", "--title", "Root edited via pp"])


def test_pp_on_root_resolves_to_itself(tasks_root: Path) -> None:
    s1 = create_task("Story one").task_id
    assert_invoke(app, ["edit", s1, "--title", "Set recent"])  # recent = s01

    # pp -> parent(s01)=s01 -> parent(s01)=s01
    assert_invoke(app, ["edit", "pp", "--title", "Root edited via pp"])


def test_pp_errors_when_no_recent(tasks_root: Path) -> None:
    assert_invoke(app, ["edit", "pp", "--title", "nope"], expect_error=True)


def test_pp_does_not_update_recent(tasks_root: Path) -> None:
    s1 = create_task("Story one").task_id
    t01 = add_subtask(s1, "Task A", details="d").task_id
    t0101 = add_subtask(t01, "Sub A1").task_id
    assert_invoke(app, ["start", t0101])  # recent = s01t0101

    assert_invoke(app, ["edit", "pp", "--title", "Grandparent edited via pp"])
    assert _read_recent(tasks_root) == t0101


# ---------------------------------------------------------------------------
# Resolve 'ppNN' / 'ppNNNN...' reference
# ---------------------------------------------------------------------------


def test_pp_digits_resolves_uncle(tasks_root: Path) -> None:
    s1 = create_task("Story one").task_id
    t01 = add_subtask(s1, "Task A", details="d").task_id
    add_subtask(t01, "Sub A1")
    t0101 = add_subtask(t01, "Sub A1").task_id
    add_subtask(s1, "Task B")
    assert_invoke(app, ["start", t0101])  # recent = s01t0101

    # pp02 -> parent(s01t0101)=s01t01 -> parent(s01t01)=s01 + t02 -> s01t02
    assert_invoke(app, ["edit", "pp02", "--title", "Uncle edited via pp02"])


def test_pp_digits_errors_when_no_recent(tasks_root: Path) -> None:
    assert_invoke(app, ["edit", "pp01", "--title", "nope"], expect_error=True)


def test_pp_digits_errors_for_nonexistent_task(tasks_root: Path) -> None:
    s1 = create_task("Story one").task_id
    t01 = add_subtask(s1, "Task A", details="d").task_id
    t0101 = add_subtask(t01, "Sub A1").task_id
    assert_invoke(app, ["start", t0101])  # recent = s01t0101

    # pp99 -> s01t99 which doesn't exist
    assert_invoke(app, ["edit", "pp99", "--title", "nope"], expect_error=True)


def test_ppp_resolves_three_levels_up(tasks_root: Path) -> None:
    s1 = create_task("Story one").task_id
    t01 = add_subtask(s1, "Task A", details="d").task_id
    t0101 = add_subtask(t01, "Sub A1", details="d").task_id
    t010101 = add_subtask(t0101, "Sub A1a").task_id
    assert_invoke(app, ["start", t010101])  # recent = s01t010101

    # ppp: s01t010101 -> s01t0101 -> s01t01 -> s01
    assert_invoke(app, ["edit", "ppp", "--title", "Three levels up via ppp"])


# ---------------------------------------------------------------------------
# Resolve 'qNN' / 'qNNNN...' reference
# ---------------------------------------------------------------------------


def test_q_digits_resolves_child(s1: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Task A", details="d").task_id
    add_subtask(t01, "Sub A1")
    assert_invoke(app, ["edit", t01, "--title", "Set recent"])  # recent = s01t01

    # q01 -> s01t01 + 01 -> s01t0101
    assert_invoke(app, ["edit", "q01", "--title", "Child edited via q01"])


def test_q_digits_resolves_from_root(tasks_root: Path) -> None:
    s1 = create_task("Story one").task_id
    add_subtask(s1, "Task A")
    # recent = s01 (root)
    # q01 -> s01 + t01 -> s01t01
    assert_invoke(app, ["edit", "q01", "--title", "Child of root via q01"])


def test_q_deep_digits_resolves_nested(tasks_root: Path) -> None:
    s1 = create_task("Story one").task_id
    t01 = add_subtask(s1, "Task A", details="d").task_id
    add_subtask(t01, "Sub A1")
    # recent = s01t01 (from add_subtask targeting s01t01)
    # reset recent to s01 so we can test deep navigation
    assert_invoke(app, ["edit", s1, "--title", "Set recent to root"])
    # q0101 -> s01 + t0101 -> s01t0101
    assert_invoke(app, ["edit", "q0101", "--title", "Deep child via q0101"])


def test_q_digits_errors_when_no_recent(tasks_root: Path) -> None:
    assert_invoke(app, ["edit", "q01", "--title", "nope"], expect_error=True)


def test_q_digits_errors_for_nonexistent_child(s1: str, tasks_root: Path) -> None:
    add_subtask(s1, "Task A")
    # recent = s01
    # q99 -> s01t99 which doesn't exist
    assert_invoke(app, ["edit", "q99", "--title", "nope"], expect_error=True)


def test_q_digits_does_not_update_recent(tasks_root: Path) -> None:
    s1 = create_task("Story one").task_id
    t01 = add_subtask(s1, "Task A", details="d").task_id
    add_subtask(t01, "Sub A1")
    assert_invoke(app, ["edit", t01, "--title", "Set recent"])  # recent = s01t01

    # q01 resolves to s01t0101 — but since it's a shortcut, recent must stay as t01
    assert_invoke(app, ["edit", "q01", "--title", "Child edited via q01"])
    assert _read_recent(tasks_root) == t01


def test_p_digits_does_not_update_recent(s1: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Task A").task_id
    add_subtask(s1, "Task B")
    assert_invoke(app, ["start", t01])  # recent = s01t01

    # p02 resolves to s01t02 — but since it's a shortcut, recent must stay as t01
    assert_invoke(app, ["edit", "p02", "--title", "Sibling edited via p02"])
    assert _read_recent(tasks_root) == t01


# ---------------------------------------------------------------------------
# add/add-many with shortcuts must not overwrite 'recent' (s15t07)
# ---------------------------------------------------------------------------


def test_add_with_q_shortcut_does_not_override_recent(
    s1: str, tasks_root: Path
) -> None:
    t01 = add_subtask(s1, "Task A").task_id
    assert_invoke(app, ["start", t01])  # recent = s01t01

    # add via shortcut q (resolves parent to s01) — recent must stay as t01
    assert_invoke(app, ["add", "q", "New subtask"])
    assert _read_recent(tasks_root) == t01


def test_add_many_with_q_shortcut_does_not_override_recent(
    s1: str, tasks_root: Path
) -> None:
    t01 = add_subtask(s1, "Task A").task_id
    assert_invoke(app, ["start", t01])  # recent = s01t01

    # add-many via shortcut q — recent must stay as t01
    assert_invoke(app, ["add-many", "q"], input="New subtask\n\n")
    assert _read_recent(tasks_root) == t01


# ---------------------------------------------------------------------------
# Multiple tasks update recent to common ancestor (s09t12)
# ---------------------------------------------------------------------------


def test_start_multiple_saves_common_ancestor(s1: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Task A").task_id
    t02 = add_subtask(s1, "Task B").task_id
    assert_invoke(app, ["start", t01, t02])
    # common ancestor of s01t01 and s01t02 is s01
    assert _read_recent(tasks_root) == s1


def test_done_multiple_saves_common_ancestor(s1: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Task A").task_id
    t02 = add_subtask(s1, "Task B").task_id
    assert_invoke(app, ["done", t01, t02])
    assert _read_recent(tasks_root) == s1


def test_cancel_multiple_saves_common_ancestor(s1: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Task A").task_id
    t02 = add_subtask(s1, "Task B").task_id
    assert_invoke(app, ["cancel", t01, t02])
    assert _read_recent(tasks_root) == s1


def test_reset_multiple_saves_common_ancestor(s1: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Task A").task_id
    t02 = add_subtask(s1, "Task B").task_id
    assert_invoke(app, ["start", t01, t02])
    assert_invoke(app, ["reset", t01, t02])
    assert _read_recent(tasks_root) == s1


# ---------------------------------------------------------------------------
# q-refs must not break when multiple tasks are passed (s09t12)
# ---------------------------------------------------------------------------


def test_move_q_refs_resolve_correctly(tasks_root: Path) -> None:
    """Moving q01 q02 must resolve both refs against the same recent."""
    s1 = create_task("Story one").task_id
    s2 = create_task("Story two").task_id
    add_subtask(s1, "Task A")
    add_subtask(s1, "Task B")

    assert_invoke(app, ["edit", s1, "--title", "Story one"])  # recent = s01

    result = assert_invoke(app, ["move", "q01", "q02", "--parent", s2])
    assert "moved" in result.output

    # Both tasks should have been moved to s02
    assert f"{s2}t01" in result.output
    assert f"{s2}t02" in result.output


def test_move_update_to_parent(tasks_root: Path) -> None:
    """Moving via q-refs must not change recent."""
    s1 = create_task("Story one").task_id
    s2 = create_task("Story two").task_id
    add_subtask(s1, "Task A")

    assert_invoke(app, ["edit", s1, "--title", "Story one"])  # recent = s01

    assert_invoke(app, ["move", "q01", "--parent", s2])
    assert _read_recent(tasks_root) == s2


def test_start_q_refs_resolve_correctly(tasks_root: Path) -> None:
    """Starting q01 q02 must resolve both against the same recent."""
    s1 = create_task("Story one").task_id
    t01 = add_subtask(s1, "Task A").task_id
    add_subtask(s1, "Task B")

    assert_invoke(app, ["edit", s1, "--title", "Story one"])  # recent = s01

    result = assert_invoke(app, ["start", "q01", "q02"])
    assert t01 in result.output  # s01t01 resolved
    assert f"{s1}t02" in result.output  # s01t02 resolved


def test_move_direct_refs_saves_common_ancestor(tasks_root: Path) -> None:
    """Moving direct refs updates recent to common ancestor of post-move IDs."""
    s1 = create_task("Story one").task_id
    s2 = create_task("Story two").task_id
    t01 = add_subtask(s1, "Task A").task_id
    t02 = add_subtask(s1, "Task B").task_id

    assert_invoke(app, ["move", t01, t02, "--parent", s2])
    # post-move IDs: s02t01 and s02t02 — common ancestor is s02
    assert _read_recent(tasks_root) == s2
