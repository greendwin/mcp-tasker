from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from typing import Generic, TypeVar

from tasker.base_types import Task, TaskStatus

_T = TypeVar("_T")


@dataclass(slots=True)
class Merged(Generic[_T]):
    value: _T


@dataclass(slots=True)
class TaskMergeResult:
    status: Merged[TaskStatus] | None
    title: Merged[str] | None
    slug: Merged[str | None] | None
    description: Merged[str | None] | None
    extra_sections: Merged[str | None] | None


@dataclass(slots=True)
class SubtaskMergeEntry:
    id: str
    title: Merged[str] | None
    status: Merged[TaskStatus] | None


def merge_subtask_lists(
    base: list[Task] | None,
    ours: list[Task],
    theirs: list[Task],
) -> list[SubtaskMergeEntry]:
    base_map = {t.id: t for t in base} if base is not None else {}
    ours_map = {t.id: t for t in ours}
    theirs_map = {t.id: t for t in theirs}

    has_base = base is not None

    # determine base-order IDs, ours-only additions, theirs-only additions
    base_ids = list(base_map) if base is not None else []
    base_id_set = set(base_ids)

    # IDs added on both sides (not in base) -- appended after base entries in ours order
    both_added = (set(ours_map) & set(theirs_map)) - base_id_set

    ours_only_additions = [
        t.id for t in ours if t.id not in base_id_set and t.id not in both_added
    ]
    theirs_only_additions = [
        t.id for t in theirs if t.id not in base_id_set and t.id not in both_added
    ]

    # build ordered ID list: base order + both-added at ours position,
    # then ours-only, then theirs-only.
    # "Both added" entries are appended after base entries, in ours order.
    ordered_ids: list[str] = []
    # first pass: base IDs
    ordered_ids.extend(base_ids)

    # insert both-added entries in ours order
    for t in ours:
        if t.id in both_added:
            ordered_ids.append(t.id)

    ordered_ids.extend(ours_only_additions)
    ordered_ids.extend(theirs_only_additions)

    result: list[SubtaskMergeEntry] = []
    merge = partial(_merge_field, has_base=has_base)

    for tid in ordered_ids:
        in_base = tid in base_map
        in_ours = tid in ours_map
        in_theirs = tid in theirs_map

        if in_base and in_ours and in_theirs:
            # Three-way merge
            b, o, t = base_map[tid], ours_map[tid], theirs_map[tid]
            result.append(
                SubtaskMergeEntry(
                    id=tid,
                    title=merge(b.title, o.title, t.title),
                    status=merge(b.status, o.status, t.status),
                )
            )
        elif in_base and in_ours and not in_theirs:
            # theirs deleted
            b, o = base_map[tid], ours_map[tid]
            if o.title == b.title and o.status == b.status:
                # Unchanged in ours -- accept delete
                continue

            # delete-modify conflict
            result.append(SubtaskMergeEntry(id=tid, title=None, status=None))
        elif in_base and not in_ours and in_theirs:
            # ours deleted
            b, t = base_map[tid], theirs_map[tid]
            if t.title == b.title and t.status == b.status:
                # Unchanged in theirs -- accept delete
                continue

            # delete-modify conflict
            result.append(SubtaskMergeEntry(id=tid, title=None, status=None))
        elif in_base and not in_ours and not in_theirs:
            # both deleted -- omit
            continue

        elif not in_base and in_ours and in_theirs:
            # both added -- two-way merge (no base)
            o, t = ours_map[tid], theirs_map[tid]
            result.append(
                SubtaskMergeEntry(
                    id=tid,
                    title=_merge_field(None, o.title, t.title, has_base=False),
                    status=_merge_field(None, o.status, t.status, has_base=False),
                )
            )
        elif not in_base and in_ours and not in_theirs:
            # ours addition
            o = ours_map[tid]
            result.append(
                SubtaskMergeEntry(
                    id=tid,
                    title=Merged(o.title),
                    status=Merged(o.status),
                )
            )
        elif not in_base and not in_ours and in_theirs:
            # theirs addition
            t = theirs_map[tid]
            result.append(
                SubtaskMergeEntry(
                    id=tid,
                    title=Merged(t.title),
                    status=Merged(t.status),
                )
            )

    return result


def merge_scalar_fields(
    base: Task | None,
    ours: Task,
    theirs: Task,
) -> TaskMergeResult:
    if ours.id != theirs.id:
        raise ValueError(
            f"Cannot merge tasks with different IDs: {ours.id!r} vs {theirs.id!r}"
        )

    merge = partial(_merge_field, has_base=base is not None)

    return TaskMergeResult(
        status=merge(base.status if base else None, ours.status, theirs.status),
        title=merge(base.title if base else None, ours.title, theirs.title),
        slug=merge(base.slug if base else None, ours.slug, theirs.slug),
        description=merge(
            base.description if base else None,
            ours.description,
            theirs.description,
        ),
        extra_sections=merge(
            base.extra_sections if base else None,
            ours.extra_sections,
            theirs.extra_sections,
        ),
    )


def _merge_field(
    base_val: _T | None,
    ours_val: _T,
    theirs_val: _T,
    *,
    has_base: bool,
) -> Merged[_T] | None:
    if ours_val == theirs_val:
        return Merged(ours_val)

    if has_base:
        if base_val == theirs_val:
            return Merged(ours_val)
        if base_val == ours_val:
            return Merged(theirs_val)

    return None
