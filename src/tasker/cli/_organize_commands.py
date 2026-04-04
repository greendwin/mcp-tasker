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
from ._resolve_task import resolve_ref, save_recent_task


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

            task = repo.resolve_ref(tp.task_ref)
            if task.is_closed:
                task_refs.append(tp.task_ref)

    for task_ref in task_refs:
        task = resolve_ref(repo, task_ref)

        if not console.json_output and not is_root_task_id(task.id):
            _report_not_root_task(task)
            raise typer.Exit(1)

        if not force and not console.json_output and not task.is_closed:
            _report_open_task(task)
            raise typer.Exit(1)

        forced = repo.archive_root_task(task, force=force)

        if forced:
            console.print("[yellow]Forcibly cancelled subtasks:[/yellow]")
            for t in forced:
                console.print(
                    f"  - [blue]{t.id}[/blue]: {t.title}",
                    json_output={"forced_task_ids": JsonAppend(t.id)},
                )

        console.print(
            f"[green]Task [blue]{task.ref}[/blue] archived[/green]",
            json_output={"task_refs": JsonAppend(task.ref)},
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
    need_preview: list[Task] = []
    for task_ref in task_refs:
        ref = repo.unarchive_root_task(task_ref)
        save_recent_task(repo, ref.task_id)

        console.print(
            f"[green]Task [blue]{ref.task_ref}[/blue] unarchived[/green]",
            json_output={"task_refs": JsonAppend(ref.task_ref)},
        )

        task = repo.resolve_ref(ref.task_id)
        need_preview.append(task)

    if need_preview:
        print_parent_preview(repo, *need_preview)


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
    repo: TaskRepo = Depends(get_task_repo),
) -> None:
    if parent_ref is not None and root:
        raise TaskerError("Cannot specify both --parent and --root.", json_output={})

    if parent_ref is None and not root:
        raise TaskerError("Specify --parent <ref> or --root.", json_output={})

    new_parent = (
        resolve_ref(repo, parent_ref, auto_unarchive=True)
        if parent_ref is not None
        else None
    )

    if new_parent is not None:
        console.print("", end="", json_output={"parent_ref": new_parent.ref})

    for k, task_ref in enumerate(task_refs):
        task = resolve_ref(repo, task_ref, auto_unarchive=True)
        renames = repo.move_task(task, new_parent=new_parent)

        # save regenerated id
        save_recent_task(repo, task.id)

        if k > 0:
            console.print("")

        if not renames:
            # idempotent — task is already at the requested location
            console.print(
                f"[green]Task [blue]{task.ref}[/blue]"
                " is already in the requested location[/green]",
                json_output={"task_refs": JsonAppend(task.ref), "already": True},
            )

            print_parent_preview(repo, task)
            continue

        if new_parent is None:
            console.print(
                f"[green]Task [blue]{task.ref}[/blue] moved to root[/green]",
                json_output={"task_refs": JsonAppend(task.ref)},
            )
        else:
            console.print(
                f"[green]Task [blue]{task.ref}[/blue]"
                f" moved under [blue]{new_parent.ref}[/blue][/green]",
                json_output={"task_refs": JsonAppend(task.ref)},
            )

        console.print("[yellow]Renamed tasks:[/yellow]")
        for r in renames:
            console.print(
                f"  [cyan]{r.old_id}[/cyan] → [blue]{r.new_id}[/blue]",
                json_output={
                    "renames": JsonAppend({"old_id": r.old_id, "new_id": r.new_id})
                },
            )

        print_parent_preview(repo, task)
