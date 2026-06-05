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
