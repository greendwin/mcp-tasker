from typing import Annotated, NamedTuple, Optional

import typer
from typer_di import Depends

from tasker.base_types import Task, is_root_task_id, walk_tasks
from tasker.exceptions import TaskerError, TaskValidateError
from tasker.parse import detect_task_type, normalize_task_id, parse_task_ref
from tasker.repo import TaskRename, TaskRepo, group_at_anchor
from tasker.resolve import ResolvedRef, resolve_ref, save_recent_for_refs
from tasker.todo import load_todo_ids, save_todo_ids
from tasker.utils import JsonAppend, console

from ._common import app, complete_task_ref, get_task_repo, unarchive_task
from ._helpers import edit_task_in_editor
from ._print_utils import format_task_list_item, print_parent_preview


@app.command("arch", hidden=True)
@app.command("archive", help="Archive a completed root task.")
def cmd_archive_task(
    *,
    task_refs: Annotated[
        Optional[list[str]],
        typer.Argument(
            help="Root task ID(s) to archive.", autocompletion=complete_task_ref
        ),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", help="Cancel open subtasks before archiving."),
    ] = False,
    all_closed: Annotated[
        bool,
        typer.Option("--closed", help="Archive all closed (done/cancelled) stories."),
    ] = False,
    repo: TaskRepo = Depends(get_task_repo),
) -> None:
    if not task_refs and not all_closed:
        raise TaskerError("Specify <task_ref> or --closed.")

    if not task_refs:
        task_refs = []

    if all_closed:
        for task_path in repo.list_root_tasks():
            tp = detect_task_type(task_path)
            if tp is None:
                # skip broken files
                continue

            if tp.task_id in task_refs or tp.task_ref in task_refs:
                continue

            if repo.resolve_ref(tp.task_ref).is_closed:
                task_refs.append(tp.task_ref)

    for task_ref in task_refs:
        ref = resolve_ref(repo, task_ref)

        if not is_root_task_id(ref.task.id):
            raise TaskValidateError(
                f"Only root tasks can be archived, {ref.task.id!r} is a subtask.",
                task_ref=ref.task.ref,
            )

        if ref.task.archived:
            console.print(
                f"[green]Task [blue]{ref.task_ref}[/blue]"
                " was already archived[/green]",
                context={"task_refs": JsonAppend(ref.task_ref), "already": True},
            )
            continue

        if not force and not ref.task.is_closed:
            raise TaskValidateError(
                f"Task {ref.task.id!r} is not closed. "
                "Use --force to cancel open subtasks and archive",
                task_ref=ref.task.id,
            )

        forced = repo.archive_root_task(ref.task, force=force)
        _remove_archived_from_todo(repo, ref.task)

        console.print(
            f"[green]Task [blue]{ref.task_ref}[/blue] archived[/green]",
            context={"task_refs": JsonAppend(ref.task_ref)},
        )

        if forced:
            console.print("[yellow]Forcibly cancelled subtasks:[/yellow]")
            for t in forced:
                console.print(
                    format_task_list_item(t, indent=1),
                    context={"forced_task_ids": JsonAppend(t.id)},
                )


def _remove_archived_from_todo(repo: TaskRepo, task: Task) -> None:
    todo_ids = load_todo_ids(repo)
    if not todo_ids:
        return

    task_ids = {t.id for t in walk_tasks(task)}
    updated = [tid for tid in todo_ids if tid not in task_ids]
    if updated != todo_ids:
        save_todo_ids(repo, updated)


@app.command("unarch", hidden=True)
@app.command("unarchive", help="Restore an archived root task.")
def cmd_unarchive_task(
    *,
    task_refs: Annotated[
        list[str],
        typer.Argument(
            help="Root task ID(s) to unarchive.", autocompletion=complete_task_ref
        ),
    ],
    repo: TaskRepo = Depends(get_task_repo),
) -> None:
    unarchived = []
    for task_ref in task_refs:
        ref = resolve_ref(repo, task_ref)

        if not is_root_task_id(ref.task.id):
            raise TaskValidateError(
                f"Only root tasks can be unarchived, {ref.task.id!r} is a subtask.",
                task_ref=ref.task.ref,
            )

        if not ref.task.archived:
            console.print(
                f"[green]Task [blue]{ref.task_ref}[/blue]"
                " was already unarchived[/green]",
                context={"task_refs": JsonAppend(ref.task_ref), "already": True},
            )
            unarchived.append(ref.task)
            continue

        repo.unarchive_root_task(task_ref)

        console.print(
            f"[green]Task [blue]{ref.task_ref}[/blue] unarchived[/green]",
            context={"task_refs": JsonAppend(ref.task_ref)},
        )

        task = repo.resolve_ref(ref.task.id)
        unarchived.append(task)

    save_recent_for_refs(repo, *unarchived)
    print_parent_preview(repo, *unarchived)


@app.command("move", help="Move a task under a new parent or to root level.")
def cmd_move_task(
    *,
    task_refs: Annotated[
        list[str],
        typer.Argument(help="Task ID(s) to move.", autocompletion=complete_task_ref),
    ],
    parent_ref: Annotated[
        Optional[str],
        typer.Option(
            "--parent",
            "-p",
            help="New parent task ID.",
            autocompletion=complete_task_ref,
        ),
    ] = None,
    root: Annotated[
        bool,
        typer.Option("--root", help="Move task to root level (make it a story)."),
    ] = False,
    delete: Annotated[
        bool,
        typer.Option("--delete", help="Delete the task instead of moving it."),
    ] = False,
    id_ref: Annotated[
        Optional[str],
        typer.Option(
            "--id",
            help="Move the task to this explicit ID (resolves the implied parent).",
        ),
    ] = None,
    editor: Annotated[
        bool,
        typer.Option("--editor", "-e", help="Open task file in editor after moving."),
    ] = False,
    repo: TaskRepo = Depends(get_task_repo),
) -> None:
    flags = sum([parent_ref is not None, root, delete, id_ref is not None])
    if flags > 1:
        raise TaskerError("Specify only one of --parent, --root, --delete, or --id.")

    if flags == 0:
        raise TaskerError("Specify --parent <ref>, --root, --delete, or --id.")

    if editor and delete:
        raise TaskerError("--editor cannot be used with --delete.")

    # Resolve all refs upfront to avoid mid-loop recent changes.
    resolved_tasks = [resolve_ref(repo, ref) for ref in task_refs]

    new_id: str | None = None
    new_parent: ResolvedRef | None = None
    if parent_ref is not None:
        new_id = None
        new_parent = resolve_ref(repo, parent_ref)
        console.set_context("parent_ref", new_parent.task_ref)
    elif id_ref is not None:
        res = _resolve_id_ref_param(repo, id_ref, resolved_tasks)
        if res is None:
            console.print(
                f"[green]Task [blue]{resolved_tasks[0].task.ref}[/blue]"
                " is already in the requested location[/green]",
                context={
                    "task_refs": JsonAppend(resolved_tasks[0].task.ref),
                    "already": True,
                },
            )
            return

        new_id, new_parent = res
        if new_parent:
            console.set_context("parent_ref", new_parent.task_ref)

    # auto-unarchive when moving tasks with non-closed status
    if any(not r.task.is_closed for r in resolved_tasks):
        for r in resolved_tasks:
            unarchive_task(repo, r.task)
        if new_parent is not None:
            unarchive_task(repo, new_parent.task)

    need_preview = []
    edit_ids: list[str] = []
    all_renames: list[TaskRename] = []
    for r in resolved_tasks:
        if delete:
            repo.delete_task(r.task)
            repo.flush_to_disk()

            console.print(
                f"[green]Task [blue]{r.task_ref}[/blue] deleted[/green]",
                context={"task_refs": JsonAppend(r.task_ref)},
            )

            need_preview.append(r.task)
            continue

        orig_parent_id = parse_task_ref(r.task.id).parent_id

        renames = repo.move_task(
            r.task,
            new_parent=new_parent.task if new_parent else None,
            new_id=new_id,
        )
        repo.flush_to_disk()

        if not renames:
            # idempotent — task is already at the requested location
            console.print(
                f"[green]Task [blue]{r.task_ref}[/blue]"
                " is already in the requested location[/green]",
                context={"task_refs": JsonAppend(r.task_ref), "already": True},
            )

            edit_ids.append(r.task.id)
            need_preview.append(r.task)
            continue

        if new_parent is None:
            console.print(
                f"[green]Task [blue]{r.task_ref}[/blue] moved to root[/green]",
                context={"task_refs": JsonAppend(r.task_ref)},
            )
        elif new_id is not None and orig_parent_id == new_parent.task.id:
            console.print(
                f"[green]Task [blue]{r.task_ref}[/blue]"
                f" renamed to [blue]{new_id}[/blue][/green]",
                context={"task_refs": JsonAppend(r.task_ref)},
            )
        else:
            console.print(
                f"[green]Task [blue]{r.task_ref}[/blue]"
                f" moved under [blue]{new_parent.task_ref}[/blue][/green]",
                context={"task_refs": JsonAppend(r.task_ref)},
            )

        all_renames.extend(renames)
        edit_ids.append(renames[0].new_id)
        need_preview.append(r.task)

    if all_renames:
        console.print("")
        _print_renamed_tasks(all_renames)

    if not delete:
        # include parent link to recent list
        if new_parent:
            resolved_tasks.append(new_parent)
        save_recent_for_refs(repo, *resolved_tasks)

    print_parent_preview(repo, *need_preview)

    if editor:
        for task_id in edit_ids:
            task = repo.resolve_ref(task_id)
            edit_task_in_editor(repo, task)


def _print_renamed_tasks(renames: list[TaskRename]) -> None:
    console.print("[yellow]Renamed tasks:[/yellow]")
    for rn in renames:
        console.print(
            f"  [cyan]{rn.old_id}[/cyan] → [blue]{rn.new_id}[/blue]",
            context={"renames": JsonAppend({"old_id": rn.old_id, "new_id": rn.new_id})},
        )


@app.command(
    "order",
    help="Reorder same-parent siblings: group <moved...> at <anchor>'s slot.",
)
def cmd_order_tasks(
    *,
    task_refs: Annotated[
        list[str],
        typer.Argument(
            help="Task IDs to edit ordering.",
            autocompletion=complete_task_ref,
        ),
    ],
    clear: Annotated[
        bool,
        typer.Option("--clear", help="Clear order from the listed tasks."),
    ] = False,
    repo: TaskRepo = Depends(get_task_repo),
) -> None:
    assert task_refs, "at least one element is expected"

    if clear:
        _clear_tasks_ordering(repo, task_refs)
        return

    anchor_ref, *moved_refs = task_refs

    if not moved_refs:
        console.print(
            "[yellow]Warning:[/yellow] Specify at least one task to "
            "place after the anchor.\n\n"
            "Note: Use `--front` flag to move your task to "
            "the beginning of the task list."
        )
        return

    anchor = resolve_ref(repo, anchor_ref)
    moved = [resolve_ref(repo, p) for p in moved_refs]

    console.print(
        f"Grouping tasks after [green]{anchor.task.id}[/green]: "
        f"{', '.join(p.task.id for p in moved)}"
    )

    moved_tasks = [p.task for p in moved]
    renames = _ensure_same_parent(repo, anchor.task, moved_tasks)

    # add summary after renames
    if console.json_output:
        console.append_context("task_refs", anchor.task.id)
        for p in moved:
            console.append_context("task_refs", p.task.id)

    if renames:
        _print_renamed_tasks(renames)
        repo.flush_to_disk()

    # note: update recents after all task renames performed
    save_recent_for_refs(repo, anchor, *moved)

    # all tasks must be upgraded to file-based
    repo.upgrade_to_filebased(anchor.task)
    for task in moved_tasks:
        repo.upgrade_to_filebased(task)

    siblings = _collect_siblings(repo, anchor.task)
    group_at_anchor(
        siblings, anchor_id=anchor.task.id, moved_ids=[t.id for t in moved_tasks]
    )

    print_parent_preview(repo, anchor.task, *moved_tasks)

    repo.flush_to_disk()


def _clear_tasks_ordering(repo: TaskRepo, task_refs: list[str]) -> None:
    refs = [resolve_ref(repo, r) for r in task_refs]
    console.print("Reset ordering for tasks:")
    for r in sorted(refs, key=lambda x: x.task.id):
        console.print(f"  - {r.task.id}", context={"task_refs": JsonAppend(r.task.id)})
        r.task.order = None
        repo.try_downgrade_task(r.task)

    save_recent_for_refs(repo, *refs)
    repo.flush_to_disk()

    tasks = [r.task for r in refs]
    print_parent_preview(repo, *tasks)


def _ensure_same_parent(
    repo: TaskRepo, anchor: Task, moved: list[Task]
) -> list[TaskRename]:
    renames = []
    anchor_parent = repo.get_parent(anchor)
    if anchor_parent is None:
        # make sure that all moving tasks are roots
        for task in moved:
            if not is_root_task_id(task.id):
                renames.extend(
                    repo.move_task(task, new_parent=None),
                )
        return renames

    for task in moved:
        if repo.get_parent(task) is not anchor_parent:
            renames.extend(
                repo.move_task(task, new_parent=anchor_parent),
            )

    return renames


def _collect_siblings(repo: TaskRepo, task: Task) -> list[Task]:
    parent = repo.get_parent(task)
    if parent is not None:
        return [p for p in parent.subtasks if not p.deleted]

    r = []
    for task_path in repo.list_root_tasks():
        tp = detect_task_type(task_path, require_valid=True)
        r.append(repo.resolve_ref(tp.task_id))
    return r


class _ResolveIdRefResult(NamedTuple):
    new_id: str
    new_parent: ResolvedRef | None


def _resolve_id_ref_param(
    repo: TaskRepo, id_ref: str, task_refs: list[ResolvedRef]
) -> _ResolveIdRefResult | None:
    if len(task_refs) != 1:
        raise TaskerError("--id can only be used with a single task ref.")

    new_id = normalize_task_id(id_ref)
    parsed = parse_task_ref(new_id)

    if is_root_task_id(new_id):
        return _ResolveIdRefResult(new_id, None)

    r = task_refs[0]
    if r.task.id == new_id:
        # TODO: use `NoopError` for such cases
        # trying to move to itself
        return None

    if repo.try_resolve_ref(new_id) is not None:
        raise TaskValidateError(
            f"Target id {new_id!r} is already taken.",
            task_ref=new_id,
        )

    if not repo.try_resolve_ref(parsed.parent_id):
        raise TaskValidateError(
            f"Target parent {parsed.parent_id!r} does not exist.",
            task_ref=parsed.parent_id,
        )

    new_parent = resolve_ref(repo, parsed.parent_id)
    return _ResolveIdRefResult(new_id, new_parent)
