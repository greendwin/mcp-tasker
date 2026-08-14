"""
Computes new order assignments for a sibling set given an operation. Values are
internal (never surfaced to CLI/MCP) and stepped sparsely so most reorders touch
a single file; the whole set is re-spaced only when a gap can't fit the needed
distinct integers.
"""

from __future__ import annotations

from typing import Generic, NamedTuple, Protocol, Sequence, TypeVar

STEP = 1000  # defult delta between two new order values (~10 steps before collision)
MIN_STEP = 50  # minimial order distance on rearrangement (~5 steps before collision)


class OrderEntry(Protocol):
    id: str
    order: int | None


TEntry = TypeVar("TEntry", bound=OrderEntry)


class OrderKey(NamedTuple):
    is_not_ordered: bool
    order: int
    id: str


def order_key(entry: OrderEntry) -> OrderKey:
    # TODO: use this key in `Task` comparison
    # is not ordered -- should go last
    return OrderKey(entry.order is None, entry.order or 0, entry.id)


def group_at_anchor(
    siblings: list[TEntry], anchor_id: str, moved_ids: list[str]
) -> None:
    """
    Take a list of siblings and update them in-place to apply the anchor rule.
    Rearrange orders so that `moved` entries go after the anchor.
    """
    siblings.sort(key=order_key)

    by_id = {p.id: p for p in siblings}

    anchor = _get_entry(by_id, anchor_id)
    if anchor.order is None:
        # put in the end of the list if anchor is unordered itself
        anchor.order = _get_last_order(siblings, 0) + STEP

    moving = [_get_entry(by_id, id) for id in moved_ids]

    r = _collect_to_rearrange(siblings, anchor, moving)
    if r.next_entry is None:
        # can arrange freely
        for k, ent in enumerate(r.to_update):
            ent.order = anchor.order + (k + 1) * STEP
        return

    # distribute available space evenly
    assert r.next_entry.order is not None, "found entry must be ordered"
    space = r.next_entry.order - anchor.order
    for k, ent in enumerate(r.to_update):
        ent.order = anchor.order + (space * (k + 1)) // (len(r.to_update) + 1)


def _get_entry(by_id: dict[str, TEntry], id: str) -> TEntry:
    r = by_id.get(id)
    if r is None:
        raise ValueError(
            f"Entry with id `{id}` was not found in sibling list: {sorted(by_id)}"
        )
    return r


def _get_last_order(entries: Sequence[TEntry], default: int) -> int:
    last_order = None
    for p in entries:
        if p.order is None:
            continue

        if last_order is None or last_order < p.order:
            last_order = p.order

    if last_order is None:
        return default

    return last_order


class _CollectToRearrange(NamedTuple, Generic[TEntry]):
    to_update: list[TEntry]
    next_entry: TEntry | None


def _collect_to_rearrange(
    siblings: list[TEntry], anchor: TEntry, moving: list[TEntry]
) -> _CollectToRearrange[TEntry]:
    assert anchor.order is not None, "anchor must be ordered at this moment"
    excl = {p.id for p in moving}

    anchor_idx = siblings.index(anchor)
    next_entry = None
    for idx in range(anchor_idx + 1, len(siblings)):
        ent = siblings[idx]
        if ent.id in excl:
            continue

        next_entry = ent
        break

    if next_entry is None or next_entry.order is None:
        # there is no next entry to fit in, just assign new `order` values
        return _CollectToRearrange(moving, None)

    if len(moving) < next_entry.order - anchor.order:
        # can fit in-bitween
        return _CollectToRearrange(moving, next_entry)

    # if cannot fit -- lets make sure that it will have enough space
    # after re-arrangement
    need_space = (len(moving) + 1) * MIN_STEP
    to_update = list(moving)
    for k in range(anchor_idx + 1, len(siblings)):
        ent = siblings[k]
        if ent.id in excl:
            continue

        if ent.order is None:
            # the rest entries are unordered, so we can freely order collected entries
            assert all(
                p.order is None for p in siblings[k + 1 :]
            ), "all unordered entries must be in the end"
            break

        if ent.order >= anchor.order + need_space:
            # found entry with enough space
            return _CollectToRearrange(to_update, ent)

        to_update.append(ent)

    return _CollectToRearrange(to_update, None)


def group_at_front(siblings: list[TEntry], moved_ids: list[str]) -> None:
    """
    Update siblings in-place so that `moved` entries lead the ordered block.
    """
    # search first ordered entry that is not moving
    excl = set(moved_ids)
    first_entry = None
    for ent in siblings:
        if ent.id in excl:
            continue

        if ent.order is None:
            continue

        if (
            first_entry is None
            or first_entry.order is None  # note: never happend
            or first_entry.order > ent.order
        ):
            first_entry = ent

    by_id = {p.id: p for p in siblings}

    if first_entry is None or first_entry.order is None:
        # either no ordered or all ordering are moving
        for k, id in enumerate(moved_ids):
            ent = _get_entry(by_id, id)
            ent.order = (k + 1) * STEP
        return

    # move before first ordered entry
    for k, id in enumerate(moved_ids):
        ent = _get_entry(by_id, id)
        ent.order = first_entry.order - STEP * (len(moved_ids) - k)
