import os
import platform
import subprocess
from pathlib import Path
from typing import Annotated

import typer
from typer_di import Depends

from tasker.base_types import Task, TaskStatus, is_nonleaf_task
from tasker.repo import TaskRepo
from tasker.utils import JsonAppend, console

from ._common import app, get_task_repo, resolve_ref


@app.command("start", help="Mark task(s) as in-progress.")
def cmd_start_task(
    *,
    task_refs: Annotated[
        list[str], typer.Argument(help="Task ID(s) to mark in-progress.")
    ],
    repo: TaskRepo = Depends(get_task_repo),
) -> None:
    with console.catching_output():
        for task_ref in task_refs:
            task = resolve_ref(repo, task_ref, save_recent=True)

            if task.status == TaskStatus.IN_PROGRESS:
                # resave tasks in case of outdated statuses
                repo.flush_to_disk()

                console.print(
                    f"[green]Task [blue]{task.ref}[/blue]"
                    " was already started[/green]",
                    json_output={"task_refs": JsonAppend(task.ref)},
                )
                continue

            if not console.json_output and is_nonleaf_task(task):
                _report_starting_nonleaf_task(task)
                raise typer.Exit(1)

            prev_status = task.status
            repo.start_task(task)
            repo.flush_to_disk()

            if prev_status == TaskStatus.DONE:
                action = "restarted"
            else:
                action = "started"

            console.print(
                f"[green]Task [blue]{task.ref}[/blue] {action}[/green]",
                json_output={"task_refs": JsonAppend(task.ref)},
            )


def _report_starting_nonleaf_task(task: Task) -> None:
    console.print(
        f"[yellow]Task [blue]{task.ref}[/blue] has subtasks"
        " — its status is managed automatically.[/yellow]"
    )

    if task.status == TaskStatus.IN_PROGRESS:
        in_progress = [t for t in task.subtasks if t.status == TaskStatus.IN_PROGRESS]
        console.print("\nIn-progress subtasks:")
        for t in in_progress:
            console.print(f"  - [blue]{t.id}[/blue]: {t.title}")
        return

    pending = [t for t in task.subtasks if t.status == TaskStatus.PENDING]
    console.print("Start one of its pending subtasks instead.")
    if not pending:
        console.print("\n[dim]No pending subtasks.[/dim]")
        return

    console.print("\nPending subtasks:")
    for t in pending:
        console.print(f"  - [blue]{t.id}[/blue]: {t.title}")


@app.command("reset", help="Reset task(s) back to pending.")
def cmd_reset_task(
    *,
    task_refs: Annotated[
        list[str], typer.Argument(help="Task ID(s) to reset to pending.")
    ],
    repo: TaskRepo = Depends(get_task_repo),
) -> None:
    with console.catching_output():
        for task_ref in task_refs:
            task = resolve_ref(repo, task_ref, save_recent=True)

            if task.status == TaskStatus.PENDING:
                # resave tasks in case of outdated statuses
                repo.flush_to_disk()

                console.print(
                    f"[green]Task [blue]{task.ref}[/blue]"
                    " was already pending[/green]",
                    json_output={"task_refs": JsonAppend(task.ref)},
                )
                continue

            if not console.json_output and is_nonleaf_task(task):
                _report_resetting_nonleaf_task(task)
                raise typer.Exit(1)

            repo.reset_task(task)
            repo.flush_to_disk()

            console.print(
                f"[green]Task [blue]{task.ref}[/blue] reset to pending[/green]",
                json_output={"task_refs": JsonAppend(task.ref)},
            )


def _report_resetting_nonleaf_task(task: Task) -> None:
    console.print(
        f"[yellow]Task [blue]{task.ref}[/blue] has subtasks"
        " — its status is managed automatically.[/yellow]"
    )


@app.command("cancel", help="Cancel task(s).")
def cmd_cancel_task(
    *,
    task_refs: Annotated[list[str], typer.Argument(help="Task ID(s) to cancel.")],
    force: Annotated[
        bool,
        typer.Option("--force", help="Force cancel all open subtasks."),
    ] = False,
    repo: TaskRepo = Depends(get_task_repo),
) -> None:
    with console.catching_output():
        for task_ref in task_refs:
            task = resolve_ref(repo, task_ref, save_recent=True)

            if task.status == TaskStatus.CANCELLED:
                # resave tasks in case of outdated statuses
                repo.flush_to_disk()

                console.print(
                    f"[green]Task [blue]{task.ref}[/blue]"
                    " was already cancelled[/green]",
                    json_output={"task_refs": JsonAppend(task.ref)},
                )
                continue

            if not force and not console.json_output and is_nonleaf_task(task):
                _report_cancelling_nonleaf_task(task)
                raise typer.Exit(1)

            forced = repo.cancel_task(task, force=force)
            repo.flush_to_disk()

            if forced:
                console.print("[yellow]Forcibly cancelled subtasks:[/yellow]")
                for t in forced:
                    console.print(
                        f"  - [blue]{t.id}[/blue]: {t.title}",
                        json_output={
                            "forced_task_ids": JsonAppend(t.id),
                        },
                    )

            console.print(
                f"[green]Task [blue]{task.ref}[/blue] cancelled[/green]",
                json_output={"task_refs": JsonAppend(task.ref)},
            )


def _report_cancelling_nonleaf_task(
    task: Task,
) -> None:
    open_tasks = [t for t in task.subtasks if not t.is_closed]

    console.print(
        f"[yellow]Task [blue]{task.ref}[/blue] has subtasks"
        " — its status is managed automatically.[/yellow]"
    )

    if not open_tasks:
        console.print("All subtasks are already closed.")
        return

    console.print("Cancel its open subtasks first, or use [bold]--force[/bold].")
    console.print("\nOpen subtasks:")
    for t in open_tasks:
        console.print(f"  - [blue]{t.id}[/blue]: {t.title}")


@app.command("done", help="Mark task(s) as done.")
def cmd_done_task(
    *,
    task_refs: Annotated[list[str], typer.Argument(help="Task ID(s) to mark done.")],
    force: Annotated[
        bool,
        typer.Option("--force", help="Force close all open subtasks."),
    ] = False,
    repo: TaskRepo = Depends(get_task_repo),
) -> None:
    with console.catching_output():
        for task_ref in task_refs:
            task = resolve_ref(repo, task_ref, save_recent=True)

            if task.status == TaskStatus.DONE:
                # resave tasks in case of outdated statuses
                repo.flush_to_disk()

                console.print(
                    f"[green]Task [blue]{task.ref}[/blue]"
                    " was already finished[/green]",
                    json_output={"task_refs": JsonAppend(task.ref)},
                )
                continue

            if not force and not console.json_output and is_nonleaf_task(task):
                _report_finishing_nonleaf_task(task)
                raise typer.Exit(1)

            forced = repo.finish_task(task, force=force)
            repo.flush_to_disk()

            if forced:
                console.print("[yellow]Forcibly closed subtasks:[/yellow]")
                for t in forced:
                    console.print(
                        f"  - [blue]{t.id}[/blue]: {t.title}",
                        json_output={
                            "forced_task_ids": JsonAppend(t.id),
                        },
                    )

            console.print(
                f"[green]Task [blue]{task.ref}[/blue] finished[/green]",
                json_output={"task_refs": JsonAppend(task.ref)},
            )


def _report_finishing_nonleaf_task(task: Task) -> None:
    open_tasks = [t for t in task.subtasks if not t.is_closed]

    console.print(
        f"[yellow]Task [blue]{task.ref}[/blue] has subtasks"
        " — its status is managed automatically.[/yellow]"
    )

    if not open_tasks:
        console.print("All subtasks are already closed.")
        return

    console.print("Finish its open subtasks first, or use [bold]--force[/bold].")

    console.print("\nOpen subtasks:")
    for t in open_tasks:
        console.print(f"  - [blue]{t.id}[/blue]: {t.title}")


@app.command("edit", help="Edit task properties (title, details, slug).")
def cmd_edit_task(
    *,
    task_ref: Annotated[str, typer.Argument(help="Task ID to edit.")],
    title: Annotated[
        str | None,
        typer.Option("--title", "-t", help="New task title."),
    ] = None,
    details: Annotated[
        str | None,
        typer.Option("--details", "-d", help="New task description."),
    ] = None,
    slug: Annotated[
        str | None,
        typer.Option("--slug", "-s", help="New task slug."),
    ] = None,
    editor: Annotated[
        bool,
        typer.Option(
            "--editor", "-e", help="Open task file in editor after applying changes."
        ),
    ] = False,
    repo: TaskRepo = Depends(get_task_repo),
) -> None:
    with console.catching_output():
        if not editor and title is None and details is None and slug is None:
            if not console.json_output:
                # open editor by default
                editor = True
            else:
                # but not in json-output mode
                console.print(
                    "[red]Error:[/red] At least one of"
                    " --title, --details, --slug, or --editor is required.",
                    json_output={"error": "No fields to edit."},
                )
                raise typer.Exit(1)

        task = resolve_ref(repo, task_ref, save_recent=True)
        repo.edit_task(task, title=title, description=details, slug=slug)

        if editor:
            repo.upgrade_to_filebased(task)
        repo.flush_to_disk()

        if editor:
            task_path = repo.build_task_path(task)
            open_in_editor(task_path.resolve())

            # after edit many things can be changed including `slug`
            # if so - reload full tree and flush it back
            if repo.loader.check_task_changed(task):
                reload = TaskRepo(repo.root)
                _ = reload.resolve_ref(task.ref)
                reload.flush_to_disk()

        console.print(
            f"[green]Task [blue]{task.ref}[/blue] updated[/green]",
            json_output={"task_ref": task.ref},
        )


def open_in_editor(path: Path) -> None:
    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR")
    if not editor:
        editor = "notepad" if platform.system() == "Windows" else "vi"

    subprocess.run([editor, str(path)])
