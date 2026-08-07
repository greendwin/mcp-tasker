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


# --- Slice A: clear returns a task to the unset tail ---


def test_order_clear_removes_order(story: str, tasks_root: Path) -> None:
    a = add_subtask(story, "Alpha", details="Alpha").task_id
    b = add_subtask(story, "Bravo", details="Bravo").task_id
    c = add_subtask(story, "Charlie", details="Charlie").task_id

    assert_invoke(app, ["order", a, b, c])
    assert _order_of(tasks_root, b) is not None  # precondition: b is ordered

    assert_invoke(app, ["order", "--clear", b])

    assert _order_of(tasks_root, b) is None


def test_order_clear_sends_task_to_id_sorted_tail(story: str) -> None:
    a = add_subtask(story, "Alpha").task_id  # s..t01
    b = add_subtask(story, "Bravo").task_id  # s..t02
    add_subtask(story, "Charlie")  # s..t03, unset tail throughout

    assert_invoke(app, ["order", a, b])  # a, b ordered; Charlie untouched
    assert_invoke(app, ["order", "--clear", a])  # a back to the unset tail

    out = assert_invoke(app, ["view", story]).output
    # b is the only ordered task → leads; a and Charlie form the unset tail by id
    assert out.index("Bravo") < out.index("Alpha") < out.index("Charlie")


def test_order_clear_already_unset_is_noop(story: str, tasks_root: Path) -> None:
    a = add_subtask(story, "Alpha").task_id  # inline, never ordered

    story_path = _fm_file(_stored_path(tasks_root, story))
    before = story_path.read_bytes()

    assert_invoke(app, ["order", "--clear", a])

    # clearing an already-unset task touches nothing on disk and does not upgrade it
    assert _fm_file(_stored_path(tasks_root, story)).read_bytes() == before
    assert not _has_stored_file(tasks_root, a)


def test_order_clear_without_tasks_reports_clear_specific_error() -> None:
    result = assert_invoke(app, ["order", "--clear"], expect_error=True)

    out = result.output.lower()
    # the error must speak to which tasks to clear — never the base command's
    # "anchor", which is meaningless under --clear
    assert "anchor" not in out
    assert "task" in out


# --- Slice B: remaining ordered siblings stay sequenced ---


def test_order_clear_keeps_remaining_ordered_sequence(
    story: str, tasks_root: Path
) -> None:
    a = add_subtask(story, "Alpha").task_id
    b = add_subtask(story, "Bravo").task_id
    c = add_subtask(story, "Charlie").task_id

    assert_invoke(app, ["order", a, b, c])  # a < b < c
    assert_invoke(app, ["order", "--clear", b])  # drop the middle one

    oa = _order_of(tasks_root, a)
    oc = _order_of(tasks_root, c)
    assert oa is not None and oc is not None
    # the survivors stay ordered and keep their relative sequence
    assert oa < oc


def test_order_clear_all_ordered_falls_back_to_id(story: str, tasks_root: Path) -> None:
    a = add_subtask(story, "Alpha", details="Alpha").task_id  # s..t01
    b = add_subtask(story, "Bravo", details="Bravo").task_id  # s..t02

    assert_invoke(app, ["order", b, a])  # b anchors → b < a while ordered
    assert_invoke(app, ["order", "--clear", a, b])  # clear the whole ordered set

    assert _order_of(tasks_root, a) is None
    assert _order_of(tasks_root, b) is None
    out = assert_invoke(app, ["view", story]).output
    # with no orders left, siblings sort purely by id (Alpha=t01 before Bravo=t02)
    assert out.index("Alpha") < out.index("Bravo")


# --- Slice C: auto-downgrade mirrors `move` ---


def test_order_clear_downgrades_file_only_for_order(
    story: str, tasks_root: Path
) -> None:
    a = add_subtask(story, "Alpha").task_id
    b = add_subtask(story, "Bravo").task_id  # inline (no --details)

    assert not _has_stored_file(tasks_root, b)  # precondition: inline
    assert_invoke(app, ["order", a, b])  # upgrades b to a file to hold its order
    assert _has_stored_file(tasks_root, b)

    assert_invoke(app, ["order", "--clear", b])

    # b became a file solely for its order → it downgrades back to inline
    assert not _has_stored_file(tasks_root, b)


def test_order_clear_keeps_file_when_described(story: str, tasks_root: Path) -> None:
    a = add_subtask(story, "Alpha").task_id
    b = add_subtask(story, "Bravo", details="has a body").task_id  # file-backed

    assert_invoke(app, ["order", a, b])
    assert_invoke(app, ["order", "--clear", b])

    # a described task keeps its file after clear, but loses its order
    assert _has_stored_file(tasks_root, b)
    assert _order_of(tasks_root, b) is None


# --- Slice D: clear reports its result (recent + summary) ---


def test_order_clear_updates_recent(tasks_root: Path) -> None:
    s1 = create_task("Story one").task_id
    a = add_subtask(s1, "Alpha").task_id
    b = add_subtask(s1, "Bravo").task_id
    assert_invoke(app, ["order", a, b])  # order under s1

    # nudge `.recent` away from s1 with an unrelated ordering under s2
    s2 = create_task("Story two").task_id
    c = add_subtask(s2, "Charlie").task_id
    d = add_subtask(s2, "Delta").task_id
    assert_invoke(app, ["order", c, d])
    assert _read_recent(tasks_root) == s2  # precondition: recent points at s2

    assert_invoke(app, ["order", "--clear", a, b])

    # clearing under s1 repoints recent at the cleared tasks' common ancestor
    assert _read_recent(tasks_root) == s1


def test_order_clear_prints_summary(story: str) -> None:
    a = add_subtask(story, "Alpha").task_id
    b = add_subtask(story, "Bravo").task_id
    assert_invoke(app, ["order", a, b])

    result = assert_invoke(app, ["order", "--clear", a, b])

    # the command reports which tasks it cleared
    assert a in result.output and b in result.output


# --- Slice E: clear emits a structured result under --json-output ---


def test_order_clear_json_emits_cleared_ids(story: str) -> None:
    a = add_subtask(story, "Alpha").task_id
    b = add_subtask(story, "Bravo").task_id
    assert_invoke(app, ["order", a, b])

    result = assert_invoke(app, ["--json-output", "order", "--clear", a, b])

    data = json.loads(result.output)
    # the cleared tasks are reported by id, in argument order
    assert data["task_refs"] == [a, b]


# ==========================================================================
# `order --front` and `order --front --rest`
# ==========================================================================


def _view_positions(output: str, ids: list[str]) -> list[int]:
    positions = []
    for task_id in ids:
        idx = output.find(task_id)
        assert idx != -1, f"{task_id!r} not present in output:\n{output}"
        positions.append(idx)
    return positions


# --- Slice A: `--front` lands the listed block at the front ---


def test_order_front_moves_anchor_to_front(story: str) -> None:
    t01 = add_subtask(story, "One").task_id
    t02 = add_subtask(story, "Two").task_id
    t03 = add_subtask(story, "Three").task_id
    t04 = add_subtask(story, "Four").task_id

    assert_invoke(app, ["order", t01, t02, t03, t04])  # ordered t01<t02<t03<t04
    assert_invoke(app, ["order", "--front", t03])  # t03 jumps to the front

    out = assert_invoke(app, ["view", story]).output
    pos = _view_positions(out, [t03, t01, t02, t04])
    # t03 now leads; the others shift down keeping their relative order
    assert pos == sorted(pos), f"expected t03 first, got:\n{out}"


def test_order_front_places_refs_ahead_in_arg_order(story: str) -> None:
    t01 = add_subtask(story, "One").task_id
    t02 = add_subtask(story, "Two").task_id
    x = add_subtask(story, "Ex").task_id
    y = add_subtask(story, "Why").task_id

    assert_invoke(app, ["order", t01, t02])  # only t01,t02 ordered
    assert_invoke(app, ["order", "--front", x, y])  # x then y ahead of them

    out = assert_invoke(app, ["view", story]).output
    pos = _view_positions(out, [x, y, t01, t02])
    assert pos == sorted(pos), f"expected x, y ahead in arg order, got:\n{out}"


def test_order_front_no_existing_ordered_assigns_block(
    story: str, tasks_root: Path
) -> None:
    a = add_subtask(story, "Alpha", details="Alpha").task_id
    b = add_subtask(story, "Bravo", details="Bravo").task_id
    c = add_subtask(story, "Charlie", details="Charlie").task_id  # stays unset

    assert_invoke(app, ["order", "--front", a, b])

    oa = _order_of(tasks_root, a)
    ob = _order_of(tasks_root, b)
    assert oa is not None and ob is not None and oa < ob
    # the untouched sibling stays in the unset tail
    assert _order_of(tasks_root, c) is None


# --- Slice B: `--front` below the current minimum goes negative, still sorts ---


def test_order_front_below_minimum_still_sorts(story: str, tasks_root: Path) -> None:
    t01 = add_subtask(story, "One").task_id
    t02 = add_subtask(story, "Two").task_id
    t03 = add_subtask(story, "Three").task_id
    t04 = add_subtask(story, "Four").task_id

    assert_invoke(app, ["order", t01, t02, t03, t04])  # ordered t01<t02<t03<t04
    # push two tasks below the current minimum — no re-space, values go negative
    assert_invoke(app, ["order", "--front", t04, t03])

    lead = _order_of(tasks_root, t04)
    prev_min = _order_of(tasks_root, t01)
    assert lead is not None and prev_min is not None
    # the engine drops below the old minimum rather than re-spacing the set
    assert lead < 0

    out = assert_invoke(app, ["view", story]).output
    pos = _view_positions(out, [t04, t03, t01, t02])
    assert pos == sorted(pos), f"expected t04,t03 leading, got:\n{out}"


# --- Slice C: `--front` single ref is valid — not the base no-op warning ---


def test_order_front_single_ref_moves_not_warns(story: str) -> None:
    t01 = add_subtask(story, "One").task_id
    t02 = add_subtask(story, "Two").task_id
    t03 = add_subtask(story, "Three").task_id

    assert_invoke(app, ["order", t01, t02, t03])  # ordered t01<t02<t03

    result = assert_invoke(app, ["order", "--front", t03])

    # under --front a lone ref is meaningful, not a no-op: no anchor warning
    assert "at least one" not in result.output.lower()

    out = assert_invoke(app, ["view", story]).output
    assert out.index(t03) < out.index(t01), f"expected t03 to lead, got:\n{out}"


# --- Slice D: `--front` honors ADR 0004 (recent / json / preview) ---


def test_order_front_updates_recent(story: str, tasks_root: Path) -> None:
    a = add_subtask(story, "Alpha").task_id
    b = add_subtask(story, "Bravo").task_id

    assert_invoke(app, ["order", "--front", a, b])

    # both touched tasks live under the story → recent records their ancestor
    assert _read_recent(tasks_root) == story


def test_order_front_json_emits_task_refs(story: str) -> None:
    a = add_subtask(story, "Alpha").task_id
    b = add_subtask(story, "Bravo").task_id
    add_subtask(story, "Charlie")

    result = assert_invoke(app, ["--json-output", "order", "--front", a, b])

    data = json.loads(result.output)
    # the front block is reported by id, in argument order
    assert data["task_refs"] == [a, b]


def test_order_front_previews_moved_in_hierarchy(story: str) -> None:
    t01 = add_subtask(story, "One").task_id
    t02 = add_subtask(story, "Two").task_id
    x = add_subtask(story, "Ex").task_id
    y = add_subtask(story, "Why").task_id

    assert_invoke(app, ["order", t01, t02])
    result = assert_invoke(app, ["order", "--front", x, y])

    # the command previews the moved tasks in the updated tree, in new order
    out = result.output
    assert x in out and y in out
    assert out.index(x) < out.index(y), f"expected x before y in preview:\n{out}"


# --- Slice E: `--rest` rotates a total order from the anchor + mass-upgrade ---


def test_order_front_rest_rotates_from_anchor(story: str) -> None:
    t01 = add_subtask(story, "One").task_id
    t02 = add_subtask(story, "Two").task_id
    t03 = add_subtask(story, "Three").task_id
    t04 = add_subtask(story, "Four").task_id

    assert_invoke(app, ["order", t01, t02, t03, t04])  # ordered t01<t02<t03<t04
    assert_invoke(app, ["order", "--front", t03, "--rest"])

    out = assert_invoke(app, ["view", story]).output
    # anchor-onward block (t03,t04) leads; the earlier siblings follow in order
    pos = _view_positions(out, [t03, t04, t01, t02])
    assert pos == sorted(pos), f"expected rotation t03,t04,t01,t02, got:\n{out}"


def test_order_front_rest_orders_anchor_onward_leaves_earlier_unset(
    story: str, tasks_root: Path
) -> None:
    a = add_subtask(story, "Alpha").task_id
    b = add_subtask(story, "Bravo").task_id
    c = add_subtask(story, "Charlie").task_id
    d = add_subtask(story, "Delta").task_id

    assert_invoke(app, ["order", "--front", c, "--rest"])

    # --rest orders the anchor and everything sorting after it (c, d) ...
    order_c = _order_of(tasks_root, c)
    order_d = _order_of(tasks_root, d)
    assert order_c is not None, "anchor left unset"
    assert order_d is not None, "tail-after-anchor left unset"
    assert order_c < order_d

    # ... while earlier siblings (a, b) stay inline/unset and sort after the block
    assert not _has_stored_file(tasks_root, a), "a should stay inline/unset"
    assert not _has_stored_file(tasks_root, b), "b should stay inline/unset"

    out = assert_invoke(app, ["view", story]).output
    pos = _view_positions(out, [c, d, a, b])
    assert pos == sorted(pos), f"expected ordered c,d before unset a,b, got:\n{out}"


def test_order_front_rest_upgrades_inline_siblings_to_files(
    story: str, tasks_root: Path
) -> None:
    a = add_subtask(story, "Alpha").task_id  # inline (no --details)
    b = add_subtask(story, "Bravo").task_id  # inline
    c = add_subtask(story, "Charlie").task_id  # inline

    assert not _has_stored_file(tasks_root, b)  # precondition: inline
    assert not _has_stored_file(tasks_root, c)

    assert_invoke(app, ["order", "--front", a, "--rest"])

    # each sibling from the anchor onward becomes a file and gains an order
    for task_id in (a, b, c):
        assert _has_stored_file(tasks_root, task_id), f"{task_id} not upgraded"
        assert _order_of(tasks_root, task_id) is not None


# --- Slice F: `--rest` honors ADR 0004 (recent / json / preview) ---


def test_order_front_rest_updates_recent(story: str, tasks_root: Path) -> None:
    a = add_subtask(story, "Alpha").task_id
    add_subtask(story, "Bravo")
    add_subtask(story, "Charlie")

    assert_invoke(app, ["order", "--front", a, "--rest"])

    # recent records the common ancestor of the *named* refs; a lone ref is itself
    assert _read_recent(tasks_root) == a


def test_order_front_rest_json_emits_task_refs(story: str) -> None:
    t01 = add_subtask(story, "One").task_id
    t02 = add_subtask(story, "Two").task_id
    t03 = add_subtask(story, "Three").task_id
    t04 = add_subtask(story, "Four").task_id

    assert_invoke(app, ["order", t01, t02, t03, t04])

    result = assert_invoke(app, ["--json-output", "order", "--front", t03, "--rest"])

    data = json.loads(result.output)
    # task_refs reports the tasks actually reordered (anchor + tail), not the
    # untouched earlier siblings
    assert data["task_refs"] == [t03, t04]


def test_order_front_rest_previews_in_hierarchy(story: str) -> None:
    t01 = add_subtask(story, "One").task_id
    t02 = add_subtask(story, "Two").task_id
    t03 = add_subtask(story, "Three").task_id
    t04 = add_subtask(story, "Four").task_id

    assert_invoke(app, ["order", t01, t02, t03, t04])
    result = assert_invoke(app, ["order", "--front", t03, "--rest"])

    out = result.output
    pos = _view_positions(out, [t03, t04])
    assert pos == sorted(pos), f"expected rotated preview t03 before t04:\n{out}"


# --- Slice G: `--clear` is mutually exclusive with the placement flags ---


def test_order_clear_rejects_other_flags(story: str) -> None:
    a = add_subtask(story, "Alpha").task_id

    for extra in ("--front", "--rest"):
        result = assert_invoke(app, ["order", "--clear", extra, a], expect_error=True)
        # --clear cannot be combined with a placement flag; the error says so
        assert (
            "clear" in result.output.lower()
        ), f"expected a --clear conflict error for {extra}, got:\n{result.output}"
