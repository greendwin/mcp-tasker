from typing import Annotated, NoReturn

import typer
from typer_di import Depends

from tasker.base_types import Task, TaskStatus, is_nonleaf_task
from tasker.exceptions import TaskHasSubtasksError
from tasker.repo import TaskRepo
from tasker.resolve import (
    ResolvedRef,
    resolve_ref,
    save_closed_refs,
    save_recent_for_refs,
)
from tasker.todo import add_todo, remove_todo
from tasker.utils import JsonAppend, console

from ._common import app, complete_task_ref, get_task_repo
from ._helpers import edit_task_in_editor
from ._print_utils import (
    compute_markers,
    format_task_list_item,
    print_parent_preview,
    print_task,
)


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
    resolved_tasks = [resolve_ref(repo, ref) for ref in task_refs]

    need_preview: list[Task] = []
    for _, task in resolved_tasks:
        orig_status = task.status

        # note: it's ok if status was not changed
        if is_nonleaf_task(task) and task.status != TaskStatus.IN_PROGRESS:
            _fail_starting_nonleaf_task(task)

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
            context={"task_refs": JsonAppend(task.ref)},
        )
        need_preview.append(task)

    save_recent_for_refs(repo, *resolved_tasks)

    markers = compute_markers(repo, *need_preview)
    for task in need_preview:
        print_task(task, markers=markers, preview=True)


@app.command("review", help="Mark task(s) as in-review.")
@console.catching_output
def cmd_review_task(
    *,
    task_refs: Annotated[
        list[str],
        typer.Argument(
            help="Task ID(s) to mark in-review.", autocompletion=complete_task_ref
        ),
    ],
    repo: TaskRepo = Depends(get_task_repo),
) -> None:
    resolved_tasks = [resolve_ref(repo, ref) for ref in task_refs]

    need_preview: list[Task] = []
    for _, task in resolved_tasks:
        orig_status = task.status

        if is_nonleaf_task(task) and task.status != TaskStatus.IN_REVIEW:
            _fail_reviewing_nonleaf_task(task)

        repo.review_task(task)
        repo.flush_to_disk()

        if orig_status == TaskStatus.IN_REVIEW:
            action = "was already in review"
        else:
            action = "marked for review"

        console.print(
            f"[green]Task [blue]{task.ref}[/blue] {action}[/green]",
            context={"task_refs": JsonAppend(task.ref)},
        )
        need_preview.append(task)

    save_recent_for_refs(repo, *resolved_tasks)

    markers = compute_markers(repo, *need_preview)
    for task in need_preview:
        print_task(task, markers=markers, preview=True)


def _fail_reviewing_nonleaf_task(task: Task) -> NoReturn:
    if console.json_output:
        raise TaskHasSubtasksError(task)

    console.print(
        f"[yellow]Task [blue]{task.ref}[/blue] has subtasks"
        " — its status is managed automatically[/yellow]"
    )

    if task.status == TaskStatus.IN_REVIEW:
        in_review = [t for t in task.subtasks if t.status == TaskStatus.IN_REVIEW]
        console.print("\nIn-review subtasks:")
        for t in in_review:
            console.print(format_task_list_item(t, indent=1))
        raise typer.Exit(1)

    pending = [t for t in task.subtasks if t.status == TaskStatus.PENDING]
    console.print("Review one of its pending subtasks instead")
    if not pending:
        console.print("\n[dim]No pending subtasks[/dim]")
        raise typer.Exit(1)

    console.print("\nPending subtasks:")
    for t in pending:
        console.print(format_task_list_item(t, indent=1))
    raise typer.Exit(1)


def _fail_starting_nonleaf_task(task: Task) -> NoReturn:
    if console.json_output:
        raise TaskHasSubtasksError(task)

    console.print(
        f"[yellow]Task [blue]{task.ref}[/blue] has subtasks"
        " — its status is managed automatically[/yellow]"
    )

    if task.status == TaskStatus.IN_PROGRESS:
        in_progress = [t for t in task.subtasks if t.status == TaskStatus.IN_PROGRESS]
        console.print("\nIn-progress subtasks:")
        for t in in_progress:
            console.print(format_task_list_item(t, indent=1))
        raise typer.Exit(1)

    pending = [t for t in task.subtasks if t.status == TaskStatus.PENDING]
    console.print("Start one of its pending subtasks instead")
    if not pending:
        console.print("\n[dim]No pending subtasks[/dim]")
        raise typer.Exit(1)

    console.print("\nPending subtasks:")
    for t in pending:
        console.print(format_task_list_item(t, indent=1))
    raise typer.Exit(1)


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
    resolved_tasks = [resolve_ref(repo, ref) for ref in task_refs]

    need_preview: list[Task] = []
    for _, task in resolved_tasks:
        already_pending = task.status == TaskStatus.PENDING

        if is_nonleaf_task(task) and not already_pending and not force:
            _fail_resetting_nonleaf_task(task)

        forced = repo.reset_task(task, force=force)
        repo.flush_to_disk()

        if already_pending:
            action = "was already pending"
        else:
            action = "reset to pending"

        console.print(
            f"[green]Task [blue]{task.ref}[/blue] {action}[/green]",
            context={"task_refs": JsonAppend(task.ref)},
        )

        if not forced:
            need_preview.append(task)
            continue

        for t in forced:
            need_preview.append(t)
            console.append_context("forced_task_ids", t.id)

    save_recent_for_refs(repo, *resolved_tasks)
    print_parent_preview(repo, *need_preview)


def _fail_resetting_nonleaf_task(task: Task) -> NoReturn:
    if console.json_output:
        raise TaskHasSubtasksError(task)

    non_pending = [t for t in task.subtasks if t.status != TaskStatus.PENDING]

    console.print(
        f"[yellow]Task [blue]{task.ref}[/blue] has subtasks"
        " — its status is managed automatically[/yellow]"
    )

    console.print("Reset its subtasks first, or use [bold]--force[/bold]")

    if non_pending:
        console.print("\nNon-pending subtasks:")
        for t in non_pending:
            console.print(format_task_list_item(t, indent=1))

    raise typer.Exit(1)


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
    resolved_tasks = [resolve_ref(repo, ref) for ref in task_refs]

    need_preview: list[Task] = []
    closed_ids: list[str] = []
    for _, task in resolved_tasks:
        already_cancelled = task.status == TaskStatus.CANCELLED

        if is_nonleaf_task(task) and not already_cancelled and not force:
            _fail_cancelling_nonleaf_task(task)

        forced = repo.cancel_task(task, force=force)
        repo.flush_to_disk()

        if already_cancelled:
            action = "was already cancelled"
        else:
            action = "cancelled"
            closed_ids.append(task.id)

        console.print(
            f"[green]Task [blue]{task.ref}[/blue] {action}[/green]",
            context={"task_refs": JsonAppend(task.ref)},
        )

        if not forced:
            need_preview.append(task)
            continue

        for t in forced:
            need_preview.append(t)
            closed_ids.append(t.id)
            console.append_context("forced_task_ids", t.id)

    save_recent_for_refs(repo, *resolved_tasks)
    save_closed_refs(repo, closed_ids)
    print_parent_preview(repo, *need_preview)


def _fail_cancelling_nonleaf_task(task: Task) -> NoReturn:
    if console.json_output:
        raise TaskHasSubtasksError(task)

    open_tasks = [t for t in task.subtasks if not t.is_closed]

    console.print(
        f"[yellow]Task [blue]{task.ref}[/blue] has subtasks"
        " — its status is managed automatically[/yellow]"
    )

    if not open_tasks:
        console.print("All subtasks are already closed")
        raise typer.Exit(1)

    console.print("Cancel its open subtasks first, or use [bold]--force[/bold]")
    console.print("\nOpen subtasks:")
    for t in open_tasks:
        console.print(format_task_list_item(t, indent=1))
    raise typer.Exit(1)


@app.command("finish", hidden=True)
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
    resolved_tasks = [resolve_ref(repo, ref) for ref in task_refs]

    need_preview: list[Task] = []
    closed_ids: list[str] = []
    for _, task in resolved_tasks:
        already_finished = task.status == TaskStatus.DONE

        if is_nonleaf_task(task) and not already_finished and not force:
            _fail_finishing_nonleaf_task(task)

        forced = repo.finish_task(task, force=force)
        repo.flush_to_disk()

        if already_finished:
            action = "was already finished"
        else:
            action = "finished"
            closed_ids.append(task.id)

        console.print(
            f"[green]Task [blue]{task.ref}[/blue] {action}[/green]",
            context={"task_refs": JsonAppend(task.ref)},
        )

        if not forced:
            # preview task itself
            need_preview.append(task)
            continue

        for t in forced:
            need_preview.append(t)
            closed_ids.append(t.id)
            console.append_context("forced_task_ids", t.id)

    save_recent_for_refs(repo, *resolved_tasks)
    save_closed_refs(repo, closed_ids)
    print_parent_preview(repo, *need_preview)


def _fail_finishing_nonleaf_task(task: Task) -> NoReturn:
    if console.json_output:
        raise TaskHasSubtasksError(task)

    open_tasks = [t for t in task.subtasks if not t.is_closed]

    console.print(
        f"[yellow]Task [blue]{task.ref}[/blue] has subtasks"
        " — its status is managed automatically[/yellow]"
    )

    if not open_tasks:
        console.print("All subtasks are already closed")
        raise typer.Exit(1)

    console.print("Finish its open subtasks first, or use [bold]--force[/bold]")

    console.print("\nOpen subtasks:")
    for t in open_tasks:
        console.print(format_task_list_item(t, indent=1))
    raise typer.Exit(1)


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
                context={"error": "No fields to edit."},
            )
            raise typer.Exit(1)

    resolved = resolve_ref(repo, task_ref)

    if title is not None or details is not None or slug is not None:
        repo.edit_task(resolved.task, title=title, description=details, slug=slug)
        repo.flush_to_disk()

    if editor:
        edited = edit_task_in_editor(repo, resolved.task)
        resolved = ResolvedRef(resolved.task_ref, edited)

    console.print(
        f"[green]Task [blue]{resolved.task.ref}[/blue] updated[/green]",
        context={"task_ref": resolved.task.ref},
    )

    save_recent_for_refs(repo, resolved)

    markers = compute_markers(repo, resolved.task)
    print_task(resolved.task, markers=markers, preview=True)


@app.command("todo", help="Add task(s) to the TODO list.")
@console.catching_output
def cmd_todo(
    *,
    task_refs: Annotated[
        list[str],
        typer.Argument(
            help="Task ID(s) to add to TODO.", autocompletion=complete_task_ref
        ),
    ],
    repo: TaskRepo = Depends(get_task_repo),
) -> None:
    resolved_tasks = [resolve_ref(repo, ref) for ref in task_refs]

    need_preview: list[Task] = []
    for _, task in resolved_tasks:
        added = add_todo(repo, task.id)
        if added:
            action = "added to todo"
        else:
            action = "already in todo"

        console.print(
            f"[green]Task [blue]{task.ref}[/blue] {action}[/green]",
            context={"task_refs": JsonAppend(task.ref)},
        )
        need_preview.append(task)

    save_recent_for_refs(repo, *resolved_tasks)
    print_parent_preview(repo, *need_preview)


@app.command("untodo", help="Remove task(s) from the TODO list.")
@console.catching_output
def cmd_untodo(
    *,
    task_refs: Annotated[
        list[str],
        typer.Argument(
            help="Task ID(s) to remove from TODO.", autocompletion=complete_task_ref
        ),
    ],
    repo: TaskRepo = Depends(get_task_repo),
) -> None:
    resolved_tasks = [resolve_ref(repo, ref) for ref in task_refs]

    need_preview: list[Task] = []
    for _, task in resolved_tasks:
        removed = remove_todo(repo, task.id)
        if removed:
            action = "removed from todo"
        else:
            action = "was not in todo"

        console.print(
            f"[green]Task [blue]{task.ref}[/blue] {action}[/green]",
            context={"task_refs": JsonAppend(task.ref)},
        )
        need_preview.append(task)

    save_recent_for_refs(repo, *resolved_tasks)
    print_parent_preview(repo, *need_preview)
