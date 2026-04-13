from collections.abc import Iterator
from typing import Annotated, NoReturn

import typer
from typer_di import Depends

from tasker.base_types import Task, TaskStatus, is_nonleaf_task, walk_tasks
from tasker.exceptions import TaskHasSubtasksError
from tasker.parse import detect_task_type
from tasker.repo import TaskRepo
from tasker.resolve import (
    ResolvedRef,
    resolve_ref,
    save_closed_refs,
    save_recent_for_refs,
)
from tasker.utils import JsonAppend, console

from ._common import app, complete_task_ref, get_task_repo
from ._print_utils import (
    compute_markers,
    format_task_list_item,
    print_parent_preview,
    print_task,
)


@app.command("start", help="Mark task(s) as in-progress.")
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
def cmd_done_task(
    *,
    task_refs: Annotated[
        list[str],
        typer.Argument(
            help="Task ID(s) to mark done.", autocompletion=complete_task_ref
        ),
    ] = [],
    force: Annotated[
        bool,
        typer.Option("--force", help="Force close all open subtasks."),
    ] = False,
    reviewed: Annotated[
        bool,
        typer.Option(
            "--reviewed",
            "--rev",
            help="Also close every currently in-review task.",
        ),
    ] = False,
    repo: TaskRepo = Depends(get_task_repo),
) -> None:
    resolved_tasks = [resolve_ref(repo, ref) for ref in task_refs]

    if reviewed:
        mentioned_tasks = {t.task.id for t in resolved_tasks}
        for t in _iter_in_review_tasks(repo):
            if t.id not in mentioned_tasks:
                resolved_tasks.append(ResolvedRef("--review", t))

    if not resolved_tasks:
        console.print("[yellow]No tasks to close.[/yellow]")
        open_leaves = list(_iter_open_leaf_tasks(repo))
        if open_leaves:
            console.print("\nOpen tasks:")
            for t in open_leaves:
                console.print(format_task_list_item(t, indent=1))
        return

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
            console.append_context("forced_task_ids", t.id)

    save_recent_for_refs(repo, *resolved_tasks)
    save_closed_refs(repo, closed_ids)
    print_parent_preview(repo, *need_preview)


def _iter_in_review_tasks(repo: TaskRepo) -> Iterator[Task]:
    for task_path in repo.list_root_tasks(archived=False):
        tp = detect_task_type(task_path)
        root = repo.resolve_ref(tp.task_ref)
        for t in walk_tasks(root):
            if t.status == TaskStatus.IN_REVIEW:
                yield t


def _iter_open_leaf_tasks(repo: TaskRepo) -> Iterator[Task]:
    for task_path in repo.list_root_tasks(archived=False):
        tp = detect_task_type(task_path)
        root = repo.resolve_ref(tp.task_ref)
        for t in walk_tasks(root):
            if not t.is_closed and not is_nonleaf_task(t):
                yield t


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
