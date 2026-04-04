from typing import Annotated

import typer
from typer_di import Depends

from tasker.base_types import Task, TaskStatus, is_nonleaf_task
from tasker.repo import TaskRepo
from tasker.utils import JsonAppend, console

from ._common import app, complete_task_ref, get_task_repo
from ._helpers import edit_task_in_editor, format_task_list_item, print_parent_preview
from ._resolve_task import resolve_ref


@app.command("start", help="Mark task(s) as in-progress.")
@console.catching_output
def cmd_start_task(
    *,
    task_refs: Annotated[
        list[str],
        typer.Argument(
            help="Task ID(s) to mark in-progress.", autocompletion=complete_task_ref
        ),
    ],
    repo: TaskRepo = Depends(get_task_repo),
) -> None:
    need_preview: list[Task] = []
    for task_ref in task_refs:
        task = resolve_ref(repo, task_ref, save_recent=True)
        orig_status = task.status

        if is_nonleaf_task(task):
            if task.status == TaskStatus.IN_PROGRESS:
                # it'ok if status was not changed
                pass
            elif not console.json_output:
                _report_starting_nonleaf_task(task)
                raise typer.Exit(1)

        repo.start_task(task)
        repo.flush_to_disk()

        if orig_status == TaskStatus.IN_PROGRESS:
            action = "was already started"
        elif orig_status == TaskStatus.DONE:
            action = "restarted"
        else:
            action = "started"

        console.print(
            f"[green]Task [blue]{task.ref}[/blue] {action}[/green]",
            json_output={"task_refs": JsonAppend(task.ref)},
        )
        need_preview.append(task)

    for task in need_preview:
        _print_task_preview(task)


def _print_task_preview(task: Task) -> None:
    title = format_task_list_item(
        task,
        show_task_id=False,
        show_all=True,
    )
    console.print(f"\n{title}")

    if task.description:
        console.print(f"{task.description}")


def _report_starting_nonleaf_task(task: Task) -> None:
    console.print(
        f"[yellow]Task [blue]{task.ref}[/blue] has subtasks"
        " — its status is managed automatically[/yellow]"
    )

    if task.status == TaskStatus.IN_PROGRESS:
        in_progress = [t for t in task.subtasks if t.status == TaskStatus.IN_PROGRESS]
        console.print("\nIn-progress subtasks:")
        for t in in_progress:
            console.print(f"  - [blue]{t.id}[/blue]: {t.title}")
        return

    pending = [t for t in task.subtasks if t.status == TaskStatus.PENDING]
    console.print("Start one of its pending subtasks instead")
    if not pending:
        console.print("\n[dim]No pending subtasks[/dim]")
        return

    console.print("\nPending subtasks:")
    for t in pending:
        console.print(format_task_list_item(t, indent=1))


@app.command("reset", help="Reset task(s) back to pending.")
@console.catching_output
def cmd_reset_task(
    *,
    task_refs: Annotated[
        list[str],
        typer.Argument(
            help="Task ID(s) to reset to pending.", autocompletion=complete_task_ref
        ),
    ],
    force: Annotated[
        bool,
        typer.Option("--force", help="Force reset all non-pending subtasks."),
    ] = False,
    repo: TaskRepo = Depends(get_task_repo),
) -> None:
    need_preview: list[Task] = []
    for task_ref in task_refs:
        task = resolve_ref(repo, task_ref, save_recent=True)
        already_pending = task.status == TaskStatus.PENDING

        if is_nonleaf_task(task):
            if already_pending or force:
                pass
            elif not console.json_output:
                _report_resetting_nonleaf_task(task)
                raise typer.Exit(1)

        forced = repo.reset_task(task, force=force)
        repo.flush_to_disk()

        if already_pending:
            action = "was already pending"
        else:
            action = "reset to pending"

        console.print(
            f"[green]Task [blue]{task.ref}[/blue] {action}[/green]",
            json_output={"task_refs": JsonAppend(task.ref)},
        )

        if not forced:
            need_preview.append(task)
        else:
            for t in forced:
                need_preview.append(t)
                console.append_json_output("forced_task_ids", t.id)

    if need_preview:
        print_parent_preview(repo, *need_preview)


def _report_resetting_nonleaf_task(task: Task) -> None:
    non_pending = [t for t in task.subtasks if t.status != TaskStatus.PENDING]

    console.print(
        f"[yellow]Task [blue]{task.ref}[/blue] has subtasks"
        " — its status is managed automatically[/yellow]"
    )

    console.print("Reset its subtasks first, or use [bold]--force[/bold]")

    if not non_pending:
        return

    console.print("\nNon-pending subtasks:")
    for t in non_pending:
        console.print(f"  - [blue]{t.id}[/blue]: {t.title}")


@app.command("cancel", help="Cancel task(s).")
@console.catching_output
def cmd_cancel_task(
    *,
    task_refs: Annotated[
        list[str],
        typer.Argument(help="Task ID(s) to cancel.", autocompletion=complete_task_ref),
    ],
    force: Annotated[
        bool,
        typer.Option("--force", help="Force cancel all open subtasks."),
    ] = False,
    repo: TaskRepo = Depends(get_task_repo),
) -> None:
    need_preview: list[Task] = []
    for task_ref in task_refs:
        task = resolve_ref(repo, task_ref, save_recent=True)
        already_cancelled = task.status == TaskStatus.CANCELLED

        if is_nonleaf_task(task):
            if already_cancelled or force:
                pass
            elif not console.json_output:
                _report_cancelling_nonleaf_task(task)
                raise typer.Exit(1)

        forced = repo.cancel_task(task, force=force)
        repo.flush_to_disk()

        if already_cancelled:
            action = "was already cancelled"
        else:
            action = "cancelled"

        console.print(
            f"[green]Task [blue]{task.ref}[/blue] {action}[/green]",
            json_output={"task_refs": JsonAppend(task.ref)},
        )

        if not forced:
            need_preview.append(task)
        else:
            for t in forced:
                need_preview.append(t)
                console.append_json_output("forced_task_ids", t.id)

    if need_preview:
        print_parent_preview(repo, *need_preview)


def _report_cancelling_nonleaf_task(
    task: Task,
) -> None:
    open_tasks = [t for t in task.subtasks if not t.is_closed]

    console.print(
        f"[yellow]Task [blue]{task.ref}[/blue] has subtasks"
        " — its status is managed automatically[/yellow]"
    )

    if not open_tasks:
        console.print("All subtasks are already closed")
        return

    console.print("Cancel its open subtasks first, or use [bold]--force[/bold]")
    console.print("\nOpen subtasks:")
    for t in open_tasks:
        console.print(f"  - [blue]{t.id}[/blue]: {t.title}")


@app.command("done", help="Mark task(s) as done.")
@console.catching_output
def cmd_done_task(
    *,
    task_refs: Annotated[
        list[str],
        typer.Argument(
            help="Task ID(s) to mark done.", autocompletion=complete_task_ref
        ),
    ],
    force: Annotated[
        bool,
        typer.Option("--force", help="Force close all open subtasks."),
    ] = False,
    repo: TaskRepo = Depends(get_task_repo),
) -> None:
    need_preview: list[Task] = []
    for task_ref in task_refs:
        task = resolve_ref(repo, task_ref, save_recent=True)
        already_finished = task.status == TaskStatus.DONE

        if is_nonleaf_task(task):
            if already_finished or force:
                pass
            elif not console.json_output:
                _report_finishing_nonleaf_task(task)
                raise typer.Exit(1)

        forced = repo.finish_task(task, force=force)
        repo.flush_to_disk()

        if already_finished:
            action = "was already finished"
        else:
            action = "finished"

        console.print(
            f"[green]Task [blue]{task.ref}[/blue] {action}[/green]",
            json_output={"task_refs": JsonAppend(task.ref)},
        )

        if not forced:
            # preview task itself
            need_preview.append(task)
        else:
            for t in forced:
                need_preview.append(t)
                console.append_json_output("forced_task_ids", t.id)

    if need_preview:
        print_parent_preview(repo, *need_preview)


def _report_finishing_nonleaf_task(task: Task) -> None:
    open_tasks = [t for t in task.subtasks if not t.is_closed]

    console.print(
        f"[yellow]Task [blue]{task.ref}[/blue] has subtasks"
        " — its status is managed automatically[/yellow]"
    )

    if not open_tasks:
        console.print("All subtasks are already closed")
        return

    console.print("Finish its open subtasks first, or use [bold]--force[/bold]")

    console.print("\nOpen subtasks:")
    for t in open_tasks:
        console.print(f"  - [blue]{t.id}[/blue]: {t.title}")


@app.command("edit", help="Edit task properties (title, details, slug).")
@console.catching_output
def cmd_edit_task(
    *,
    task_ref: Annotated[
        str, typer.Argument(help="Task ID to edit.", autocompletion=complete_task_ref)
    ],
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

    task = resolve_ref(repo, task_ref, save_recent=True, auto_unarchive=True)
    if title is not None or details is not None or slug is not None:
        repo.edit_task(task, title=title, description=details, slug=slug)
        repo.flush_to_disk()

    if editor:
        task = edit_task_in_editor(repo, task)

    console.print(
        f"[green]Task [blue]{task.ref}[/blue] updated[/green]",
        json_output={"task_ref": task.ref},
    )

    _print_task_preview(task)
