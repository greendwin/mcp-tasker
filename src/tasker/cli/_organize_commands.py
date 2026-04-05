from typing import Annotated, Optional

import typer
from typer_di import Depends

from tasker.base_types import Task, is_root_task_id
from tasker.exceptions import TaskerError
from tasker.parse import detect_task_type
from tasker.repo import TaskRepo
from tasker.utils import JsonAppend, console

from ._common import app, complete_task_ref, get_task_repo
from ._helpers import print_parent_preview
from ._resolve_task import resolve_ref, save_recent_for_refs, unarchive_task


@app.command("arch", hidden=True)
@app.command("archive", help="Archive a completed root task.")
@console.catching_output
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
        raise TaskerError("Specify <task_ref> or --closed.", json_output={})

    if not task_refs:
        task_refs = []

    if all_closed:
        for task_path in repo.list_root_tasks():
            tp = detect_task_type(task_path)
            if tp.task_id in task_refs or tp.task_ref in task_refs:
                continue

            if repo.resolve_ref(tp.task_ref).is_closed:
                task_refs.append(tp.task_ref)

    for task_ref in task_refs:
        ref = resolve_ref(repo, task_ref)

        if not console.json_output and not is_root_task_id(ref.task.id):
            _report_not_root_task(ref.task)
            raise typer.Exit(1)

        if ref.task.archived:
            console.print(
                f"[green]Task [blue]{ref.task_ref}[/blue]"
                " was already archived[/green]",
                json_output={"task_refs": JsonAppend(ref.task_ref), "already": True},
            )
            continue

        if not force and not ref.task.is_closed:
            if not console.json_output:
                _report_open_task(ref.task)
                raise typer.Exit(1)

        forced = repo.archive_root_task(ref.task, force=force)

        if forced:
            console.print("[yellow]Forcibly cancelled subtasks:[/yellow]")
            for t in forced:
                console.print(
                    f"  - [blue]{t.id}[/blue]: {t.title}",
                    json_output={"forced_task_ids": JsonAppend(t.id)},
                )

        console.print(
            f"[green]Task [blue]{ref.task_ref}[/blue] archived[/green]",
            json_output={"task_refs": JsonAppend(ref.task_ref)},
        )


@app.command("unarch", hidden=True)
@app.command("unarchive", help="Restore an archived root task.")
@console.catching_output
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

        if not console.json_output and not is_root_task_id(ref.task.id):
            console.print(
                f"[yellow]Only root tasks can be unarchived —"
                f" [blue]{ref.task.ref}[/blue] is a subtask.[/yellow]"
            )
            raise typer.Exit(1)

        if not ref.task.archived:
            console.print(
                f"[green]Task [blue]{ref.task_ref}[/blue]"
                " was already unarchived[/green]",
                json_output={"task_refs": JsonAppend(ref.task_ref), "already": True},
            )
            unarchived.append(ref.task)
            continue

        repo.unarchive_root_task(task_ref)

        console.print(
            f"[green]Task [blue]{ref.task_ref}[/blue] unarchived[/green]",
            json_output={"task_refs": JsonAppend(ref.task_ref)},
        )

        task = repo.resolve_ref(ref.task.id)
        unarchived.append(task)

    save_recent_for_refs(repo, *unarchived)
    print_parent_preview(repo, *unarchived)


def _report_not_root_task(task: Task) -> None:
    console.print(
        f"[yellow]Only root tasks can be archived —"
        f" [blue]{task.ref}[/blue] is a subtask.[/yellow]"
    )


def _report_open_task(task: Task) -> None:
    console.print(f"[yellow]Task [blue]{task.ref}[/blue] is not closed.[/yellow]")

    open_tasks = [t for t in task.subtasks if not t.is_closed]
    if open_tasks:
        console.print("Close its open subtasks first, or use [bold]--force[/bold]")
        console.print("\nOpen subtasks:")
        for t in open_tasks:
            console.print(f"  - [blue]{t.id}[/blue]: {t.title}")
    else:
        console.print("Use [bold]--force[/bold] to cancel and archive")


@app.command("move", help="Move a task under a new parent or to root level.")
@console.catching_output
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
    repo: TaskRepo = Depends(get_task_repo),
) -> None:
    flags = sum([parent_ref is not None, root, delete])
    if flags > 1:
        raise TaskerError(
            "Specify only one of --parent, --root, or --delete.", json_output={}
        )

    if flags == 0:
        raise TaskerError(
            "Specify --parent <ref>, --root, or --delete.", json_output={}
        )

    new_parent = None
    if parent_ref is not None:
        new_parent = resolve_ref(repo, parent_ref)
        console.set_context("parent_ref", new_parent.task_ref)

    # Resolve all refs upfront to avoid mid-loop recent changes.
    resolved_tasks = [resolve_ref(repo, ref) for ref in task_refs]

    # auto-unarchive when moving tasks with non-closed status
    if any(not r.task.is_closed for r in resolved_tasks):
        for r in resolved_tasks:
            unarchive_task(repo, r.task)
        if new_parent is not None:
            unarchive_task(repo, new_parent.task)

    need_preview = []
    for r in resolved_tasks:
        if delete:
            repo.delete_task(r.task)
            repo.flush_to_disk()

            console.print(
                f"[green]Task [blue]{r.task_ref}[/blue] deleted[/green]",
                json_output={"task_refs": JsonAppend(r.task_ref)},
            )

            need_preview.append(r.task)
            continue

        renames = repo.move_task(
            r.task,
            new_parent=new_parent.task if new_parent else None,
        )
        repo.flush_to_disk()

        if not renames:
            # idempotent — task is already at the requested location
            console.print(
                f"[green]Task [blue]{r.task_ref}[/blue]"
                " is already in the requested location[/green]",
                json_output={"task_refs": JsonAppend(r.task_ref), "already": True},
            )

            need_preview.append(r.task)
            continue

        if new_parent is None:
            console.print(
                f"[green]Task [blue]{r.task_ref}[/blue] moved to root[/green]",
                json_output={"task_refs": JsonAppend(r.task_ref)},
            )
        else:
            console.print(
                f"[green]Task [blue]{r.task_ref}[/blue]"
                f" moved under [blue]{new_parent.task_ref}[/blue][/green]",
                json_output={"task_refs": JsonAppend(r.task_ref)},
            )

        console.print("[yellow]Renamed tasks:[/yellow]")
        for rn in renames:
            console.print(
                f"  [cyan]{rn.old_id}[/cyan] → [blue]{rn.new_id}[/blue]",
                json_output={
                    "renames": JsonAppend({"old_id": rn.old_id, "new_id": rn.new_id})
                },
            )

        need_preview.append(r.task)

    if not delete:
        # include parent link to recent list
        if new_parent:
            resolved_tasks.append(new_parent)
        save_recent_for_refs(repo, *resolved_tasks)

    print_parent_preview(repo, *need_preview)
