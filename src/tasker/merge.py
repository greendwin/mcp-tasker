from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from typing import Generic, TypeAlias, TypeVar

from tasker.base_types import Task, TaskStatus, build_task_ref
from tasker.parse import ParsedSubtask, parse_task
from tasker.render import render_subtask_line

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


@dataclass(slots=True)
class SubtaskMergeEntry:
    id: str
    title: Merged[str] | None
    status: Merged[TaskStatus] | None


@dataclass(slots=True)
class ConflictingSubtask:
    # note: None means was not exist
    base: ParsedSubtask | None
    # note: None means deleted
    ours: ParsedSubtask | None
    theirs: ParsedSubtask | None


MergedSubtask: TypeAlias = ParsedSubtask | ConflictingSubtask


def merge_subtask_lists(
    base_task: list[ParsedSubtask] | None,
    ours_task: list[ParsedSubtask],
    theirs_task: list[ParsedSubtask],
) -> list[MergedSubtask]:
    base_map = {t.id: t for t in base_task} if base_task is not None else {}
    ours_map = {t.id: t for t in ours_task}
    theirs_map = {t.id: t for t in theirs_task}

    task_ids = sorted(set(base_map) | set(ours_map) | set(theirs_map))

    result = []

    for tid in task_ids:
        base = base_map.get(tid)
        ours = ours_map.get(tid)
        theirs = theirs_map.get(tid)

        if ours and theirs:
            result.append(_try_merge_subtask(base, ours, theirs))
            continue

        if not ours and not theirs:
            # both deleted
            continue

        # --- either `ours` or `theirs` is missing ---

        if not base:
            # no base means it was added; one side must exist
            added = ours or theirs
            assert added is not None
            result.append(added)
            continue

        if ours == base or theirs == base:
            # one unchanged, another deleted
            continue

        # otherwise: delete-modify conflict
        result.append(ConflictingSubtask(base, ours, theirs))

    return result


def _try_merge_subtask(
    base: ParsedSubtask | None,
    ours: ParsedSubtask,
    theirs: ParsedSubtask,
) -> MergedSubtask:
    has_base = base is not None
    merge = partial(_merge_field, has_base=has_base)

    title = merge(base.title if base else None, ours.title, theirs.title)
    status = merge(base.status if base else None, ours.status, theirs.status)
    slug = merge(base.slug if base else None, ours.slug, theirs.slug)

    if title is None or status is None or slug is None:
        return ConflictingSubtask(base, ours, theirs)

    assert ours.id == theirs.id

    return ParsedSubtask(
        id=ours.id,
        slug=slug.value,
        ref=build_task_ref(ours.id, slug.value) if slug.value else ours.id,
        title=title.value,
        status=status.value,
        extended=ours.extended or theirs.extended,
    )


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


@dataclass(slots=True)
class MergeFileResult:
    content: str
    has_conflicts: bool


def _conflict_block(ours_text: str, theirs_text: str) -> str:
    r = ["<<<<<<< ours"]
    if ours_text:
        r.append(ours_text)

    # TODO: show base part

    r.append("=======")
    if theirs_text:
        r.append(theirs_text)

    r.append(">>>>>>> theirs")

    return "\n".join(r)


class _MergeComposer:
    def __init__(self) -> None:
        self.has_conflicts = False
        self.lines: list[str] = []

    def append_merged(
        self,
        fmt: str,
        /,
        merged: Merged[_T] | None,
        ours: _T,
        their: _T,
    ) -> None:
        if merged:
            if merged.value is None:
                return

            self.lines.append(fmt.format(merged.value))
            return

        self.append_conflict(
            fmt.format(ours if ours is not None else ""),
            fmt.format(their if their is not None else ""),
        )

    def append_conflict(self, ours_text: str, theirs_text: str) -> None:
        self.lines.append(_conflict_block(ours_text, theirs_text))
        self.has_conflicts = True


def merge_task_file(
    base_content: str | None,
    ours_content: str,
    theirs_content: str,
    *,
    task_id: str,
    slug: str,
    extended: bool,
) -> MergeFileResult:
    base = (
        parse_task(base_content, task_id=task_id, slug=slug, extended=extended)
        if base_content is not None
        else None
    )
    ours = parse_task(ours_content, task_id=task_id, slug=slug, extended=extended)
    theirs = parse_task(theirs_content, task_id=task_id, slug=slug, extended=extended)

    base_task = base.task if base else None
    ours_task = ours.task
    theirs_task = theirs.task

    r = _MergeComposer()

    # --- Front-matter ---
    r.lines.append("---")
    r.lines.append(f"id: {task_id}")

    fields = merge_scalar_fields(base_task, ours_task, theirs_task)
    r.append_merged("slug: {}", fields.slug, ours_task.slug, theirs_task.slug)

    r.append_merged(
        "status: {.value}", fields.status, ours_task.status, theirs_task.status
    )
    r.lines.append("---")
    r.lines.append("")
    r.append_merged("# {}", fields.title, ours_task.title, theirs_task.title)

    if fields.description is None or fields.description.value:
        # either has conflict or has description
        r.lines.append("")
    r.append_merged(
        "{}",
        fields.description,
        ours_task.description,
        theirs_task.description,
    )

    merged_entries = merge_subtask_lists(
        base.subtasks if base else None, ours.subtasks, theirs.subtasks
    )
    if merged_entries:
        r.lines.append("")
        r.lines.append("## Subtasks")
        r.lines.append("")

    for entry in merged_entries:
        if isinstance(entry, ParsedSubtask):
            r.lines.append(render_subtask_line(entry))
            continue

        r.append_conflict(
            render_subtask_line(entry.ours) if entry.ours else "",
            render_subtask_line(entry.theirs) if entry.theirs else "",
        )

    r.lines.append("")
    return MergeFileResult(content="\n".join(r.lines), has_conflicts=r.has_conflicts)
