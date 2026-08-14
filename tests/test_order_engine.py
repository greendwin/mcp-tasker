from dataclasses import dataclass

from tasker.repo._order import (
    MIN_STEP,
    group_at_anchor,
    group_at_front,
    order_key,
)


@dataclass
class _Entry:
    # minimal mutable `OrderEntry` for the pure engine — no filesystem, no Task
    id: str
    order: int | None = None


def _move_after(
    siblings: list[tuple[str, int | None]], anchor_id: str, moved_ids: list[str]
) -> dict[str, int | None]:
    # run the in-place engine and read back the resulting {id: order}
    entries = [_Entry(task_id, order) for task_id, order in siblings]
    group_at_anchor(entries, anchor_id, moved_ids)
    return {e.id: e.order for e in entries}


def _move_front(
    siblings: list[tuple[str, int | None]], moved_ids: list[str]
) -> dict[str, int | None]:
    entries = [_Entry(task_id, order) for task_id, order in siblings]
    group_at_front(entries, moved_ids)
    return {e.id: e.order for e in entries}


def _ordered_values(orders: dict[str, int | None], ids: list[str]) -> list[int]:
    # narrow to non-None in the given id order (fails loudly if any is unset)
    values: list[int] = []
    for task_id in ids:
        value = orders[task_id]
        assert value is not None, f"{task_id!r} expected ordered, got None in {orders}"
        values.append(value)
    return values


# --- Slice A: group-at-anchor free arrangement (append / all-unset) ---


def test_group_at_anchor_all_unset_assigns_spaced_block() -> None:
    orders = _move_after(
        [("a", None), ("b", None), ("c", None), ("d", None)], "a", ["b", "c"]
    )

    assert orders == {"a": 1000, "b": 2000, "c": 3000, "d": None}


def test_group_at_anchor_moves_ordered_entry_after_last() -> None:
    # x already ordered mid-set; moving it after the last entry appends past the max
    orders = _move_after([("a", 1000), ("x", 2000), ("b", 3000)], "b", ["x"])

    assert orders == {"a": 1000, "b": 3000, "x": 4000}


def test_anchor_unordered_appends_after_last_ordered() -> None:
    orders = _move_after([("a", 5000), ("z", None)], "z", [])

    assert orders == {"a": 5000, "z": 6000}


# --- Slice A: group-at-anchor fit-between (invariants that catch wrong math) ---


def test_single_insert_stays_between_neighbours() -> None:
    orders = _move_after([("a", 1000), ("b", 2000), ("x", None)], "a", ["x"])

    # anchor and follower untouched; x lands strictly between them
    assert orders["a"] == 1000
    assert orders["b"] == 2000
    assert orders["x"] is not None and 1000 < orders["x"] < 2000


def test_multi_insert_values_ascending_distinct_within_bounds() -> None:
    orders = _move_after(
        [("a", 1000), ("b", 1100), ("m", None), ("n", None), ("p", None)],
        "a",
        ["m", "n", "p"],
    )

    raw = [orders["m"], orders["n"], orders["p"]]
    assert all(v is not None for v in raw)
    seq = [v for v in raw if v is not None]
    assert seq == sorted(seq)  # argument order preserved, ascending
    assert len(set(seq)) == 3  # no collisions from the distribution formula
    assert all(1000 < v < 1100 for v in seq)  # inside the gap


def test_multi_insert_gap_too_small_respaces_with_step() -> None:
    # a gap of 2 can't hold 2 distinct midpoints → re-space, follower pushed by STEP
    orders = _move_after(
        [("a", 1000), ("b", 1002), ("m", None), ("n", None)], "a", ["m", "n"]
    )

    assert orders == {"a": 1000, "m": 2000, "n": 3000, "b": 4000}


# --- Slice A: partial-touch rearrangement (don't re-space the whole tail) ---


def test_rearrange_touches_only_needed_followers_not_all() -> None:
    # b is tight after a; c is far. Inserting x must reshuffle only x and b.
    orders = _move_after(
        [("a", 1000), ("b", 1001), ("c", 5000), ("x", None)], "a", ["x"]
    )

    assert orders["a"] == 1000  # anchor untouched
    assert orders["c"] == 5000  # far follower untouched — not a full re-space
    assert orders["x"] is not None and orders["b"] is not None
    assert 1000 < orders["x"] < orders["b"] < 5000


def test_insert_between_adjacent_triggers_respace() -> None:
    # gap of size 1 (adjacent) → local re-space of the collected followers
    orders = _move_after([("a", 1000), ("b", 1001), ("x", None)], "a", ["x"])

    assert orders == {"a": 1000, "x": 2000, "b": 3000}


# --- Slice A: argument-order & multi-move scenarios ---


def test_moved_block_preserves_argument_order() -> None:
    # moved in reverse of natural id order → result follows argument order
    orders = _move_after([("a", None), ("b", None), ("c", None)], "a", ["c", "b"])

    c, b = _ordered_values(orders, ["c", "b"])
    assert orders["a"] is not None and orders["a"] < c < b


def test_move_multiple_ordered_entries_reorders_by_argument() -> None:
    # x,y already ordered (y before x); moving [x, y] after a enforces arg order
    orders = _move_after(
        [("a", 1000), ("y", 2000), ("x", 3000), ("b", 9000)], "a", ["x", "y"]
    )

    x, y = _ordered_values(orders, ["x", "y"])
    assert orders["a"] == 1000 and orders["b"] == 9000  # endpoints untouched
    assert 1000 < x < y < 9000  # arg order (x before y), inside the gap


def test_empty_moved_list_is_noop() -> None:
    orders = _move_after([("a", 1000), ("b", 2000)], "a", [])

    assert orders == {"a": 1000, "b": 2000}


# --- Slice A (bug-red): distribution must not jam the first moved entry ---


def test_single_insert_not_jammed_against_anchor() -> None:
    orders = _move_after([("a", 1000), ("b", 2000), ("x", None)], "a", ["x"])

    x = orders["x"]
    assert x is not None
    # both neighbouring gaps need breathing room — x must be near the midpoint,
    # not packed at anchor+1 (which would force an immediate re-space next insert)
    assert x - 1000 >= MIN_STEP
    assert 2000 - x >= MIN_STEP


def test_multi_insert_first_gap_not_starved() -> None:
    orders = _move_after(
        [("a", 1000), ("b", 1100), ("m", None), ("n", None), ("p", None)],
        "a",
        ["m", "n", "p"],
    )

    first = orders["m"]
    assert first is not None
    # the gap below the first moved entry should be a fair share of the span,
    # not 1 — 4 gaps across a span of 100 → each ~25
    assert first - 1000 >= (1100 - 1000) // (3 + 1)


# --- Slice E: robustness to duplicate / gapped input ---


def test_duplicate_input_tolerated_append_after_max() -> None:
    orders = _move_after(
        [("a", 1000), ("b", 1000), ("c", 5000), ("x", None)], "c", ["x"]
    )

    assert orders == {"a": 1000, "b": 1000, "c": 5000, "x": 6000}


# --- Slice B (RED): group-at-front — moved block leads the ordered set ---


def test_front_single_lands_before_minimum() -> None:
    orders = _move_front([("a", 1000), ("b", 2000), ("x", None)], ["x"])

    x = orders["x"]
    assert x == 0


def test_front_block_preserves_order_all_before_minimum() -> None:
    orders = _move_front(
        [("a", 1000), ("b", 2000), ("m", None), ("n", None)], ["m", "n"]
    )

    m, n = _ordered_values(orders, ["m", "n"])
    assert orders["a"] == 1000 and orders["b"] == 2000
    assert m < n < 1000  # both below the minimum, argument order preserved


def test_front_never_normalize() -> None:
    orders = _move_front([("a", 1), ("b", 2000), ("x", None)], ["x"])
    assert orders == {"x": -999, "a": 1, "b": 2000}


def test_front_on_all_unset_assigns_leading_block() -> None:
    # first-ever order op via the front path → plain spaced block
    orders = _move_front([("a", None), ("b", None), ("c", None)], ["a", "b"])

    a, b = _ordered_values(orders, ["a", "b"])
    assert a < b and orders["c"] is None


# --- Slice B (bug-red): front must anchor to the minimum, not first-in-list ---


def test_front_uses_min_order_when_input_unsorted() -> None:
    # input not pre-sorted: b listed first but a has the smaller order.
    # x must lead the ordered set (below a's 1000), not anchor to b's 2000.
    orders = _move_front([("b", 2000), ("a", 1000), ("x", None)], ["x"])

    assert orders["a"] == 1000 and orders["b"] == 2000  # untouched
    x = orders["x"]
    assert x is not None and x < 1000  # strictly leads the smallest order


def test_front_multi_move_unsorted_leads_min_in_argument_order() -> None:
    # unsorted input + multi-move listed out of natural order: block must anchor
    # to the true minimum (a=1000) and preserve argument order (m before n)
    orders = _move_front(
        [("b", 3000), ("a", 1000), ("n", None), ("m", None)], ["m", "n"]
    )

    assert orders["a"] == 1000 and orders["b"] == 3000  # untouched
    m, n = _ordered_values(orders, ["m", "n"])
    assert m < n < 1000  # whole block leads the smallest order, arg order kept


# --- post-merge tolerance: order_key sorts gaps/duplicates/unset sensibly ---


def test_order_key_tolerates_gaps_duplicates_and_unset() -> None:
    # a per-file scalar merge can leave gaps, duplicate orders, or an unset
    # sibling. The sort key must still yield a stable, sensible ordering without
    # any re-densification: ordered ascend (dupes tie-broken by id), unset last.
    entries = [
        _Entry("d", None),
        _Entry("c", 10),
        _Entry("a", 10),
        _Entry("b", 500),
        _Entry("e", None),
    ]

    entries.sort(key=order_key)

    assert [e.id for e in entries] == ["a", "c", "b", "d", "e"]
