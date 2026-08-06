import json
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


# --- Slice F: cross-parent moved ref is relocated under the anchor's parent ---


def test_order_relocates_cross_parent_moved_under_anchor() -> None:
    s1 = create_task("Story one").task_id
    s2 = create_task("Story two").task_id
    a = add_subtask(s1, "Alpha").task_id
    b = add_subtask(s2, "Bravo").task_id

    assert_invoke(app, ["order", a, b])

    view1 = assert_invoke(app, ["view", s1]).output
    view2 = assert_invoke(app, ["view", s2]).output
    # Bravo is pulled under the anchor's parent and ordered right after Alpha
    assert "Alpha" in view1 and "Bravo" in view1
    assert view1.index("Alpha") < view1.index("Bravo")
    # ...and it no longer lives under its former parent
    assert "Bravo" not in view2


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


# --- Slice G: reordering root-level stories (anchor has no parent) ---


def test_order_reorders_root_level_stories(tasks_root: Path) -> None:
    s1 = create_task("One").task_id
    s2 = create_task("Two").task_id
    s3 = create_task("Three").task_id

    assert_invoke(app, ["order", s1, s3, s2])

    o1 = _order_of(tasks_root, s1)
    o3 = _order_of(tasks_root, s3)
    o2 = _order_of(tasks_root, s2)
    assert o1 is not None and o2 is not None and o3 is not None
    # anchor first, then moved in argument order (s3 before s2) at root scope
    assert o1 < o3 < o2


# --- Slice I: a subtask is promoted to root when the anchor is a root task ---


def test_order_promotes_subtask_to_root_under_root_anchor() -> None:
    s1 = create_task("Anchor root").task_id
    s2 = create_task("Story two").task_id
    sub = add_subtask(s2, "Promote me").task_id

    assert_invoke(app, ["order", s1, sub])

    # the subtask now lives at root, ordered right after the anchor
    listing = assert_invoke(app, ["list"]).output
    assert "Anchor root" in listing and "Promote me" in listing
    assert listing.index("Anchor root") < listing.index("Promote me")
    # ...and it no longer lives under its former parent
    assert "Promote me" not in assert_invoke(app, ["view", s2]).output


# --- Slice J: relocated (renamed) tasks are reported in the output ---


def test_order_prints_relocated_tasks() -> None:
    s1 = create_task("Story one").task_id
    s2 = create_task("Story two").task_id
    a = add_subtask(s1, "Alpha").task_id
    b = add_subtask(s2, "Bravo").task_id  # cross-parent → relocated + renamed

    result = assert_invoke(app, ["order", a, b])

    # the relocated task's former id is reported in the rename listing
    assert b in result.output


# --- Slice K: moved tasks are reported at their new position, in argument order ---


def test_order_reports_moved_tasks_in_new_order(story: str) -> None:
    a = add_subtask(story, "Alpha").task_id
    b = add_subtask(story, "Bravo").task_id
    c = add_subtask(story, "Charlie").task_id

    result = assert_invoke(app, ["order", a, b, c])

    out = result.output
    # the moved tasks are reported, in argument order (b before c)
    assert b in out and c in out
    assert out.index(b) < out.index(c)


def _read_recent(tasks_root: Path) -> str | None:
    path = tasks_root / ".recent"
    return path.read_text().strip() if path.exists() else None


# --- Slice M: `.recent` reflects the post-relocation common ancestor ---


def test_order_recent_uses_relocated_ancestor(tasks_root: Path) -> None:
    s1 = create_task("Story one").task_id
    s2 = create_task("Story two").task_id
    a = add_subtask(s1, "Alpha").task_id  # s01t01
    b = add_subtask(s2, "Bravo").task_id  # s02t01 → relocates under s1 to s01t02

    assert_invoke(app, ["order", a, b])

    # after relocation both ordered siblings live under s1, so their common
    # ancestor — what `.recent` records — is s1, not the pre-move root ancestor
    assert _read_recent(tasks_root) == s1


# --- Slice N: the summary line echoes the refs as typed, before any rename ---


def test_order_summary_reports_uses_old_id_before_move() -> None:
    s1 = create_task("Story one").task_id
    s2 = create_task("Story two").task_id
    a = add_subtask(s1, "Alpha").task_id  # s01t01
    b = add_subtask(s2, "Bravo").task_id  # s02t01 → relocates to s01t02

    result = assert_invoke(app, ["order", a, b])

    summary = next(line for line in result.output.splitlines() if line.strip())
    # the leading summary is an echo of the command as typed: it names the ref
    # the user gave (its pre-move id), printed before relocation. Final ids are
    # reported by the rename listing, the preview tree, and the json payload.
    assert (
        b in summary
    ), f"summary should echo the typed ref {b}, before renames:\n{result.output}"


# --- Slice O: `order` emits a structured result under --json-output ---


def test_order_json_emits_moved_ids(story: str) -> None:
    a = add_subtask(story, "Alpha").task_id
    b = add_subtask(story, "Bravo").task_id
    c = add_subtask(story, "Charlie").task_id

    result = assert_invoke(app, ["--json-output", "order", a, b, c])

    data = json.loads(result.output)
    # anchor first, then moved in argument order (b before c)
    assert data["task_refs"] == [a, b, c]


def test_order_json_reports_renames() -> None:
    s1 = create_task("Story one").task_id
    s2 = create_task("Story two").task_id
    a = add_subtask(s1, "Alpha").task_id  # s01t01
    b = add_subtask(s2, "Bravo").task_id  # s02t01 → relocates to s01t02

    result = assert_invoke(app, ["--json-output", "order", a, b])

    data = json.loads(result.output)
    new_id = f"{s1}t02"
    assert {"old_id": b, "new_id": new_id} in data["renames"]
    # moved tasks reported by their final ids (anchor first)
    assert data["task_refs"] == [a, new_id]


def test_order_json_single_arg_noop() -> None:
    a = create_task("Solo").task_id

    result = assert_invoke(app, ["--json-output", "order", a])

    data = json.loads(result.output)
    # a no-op moves nothing; the payload stays well-formed with no moved tasks
    assert data.get("task_refs", []) == []
