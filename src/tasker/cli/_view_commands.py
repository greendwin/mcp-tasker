from typing import Annotated, Any

import typer
from typer_di import Depends

from tasker.base_types import Task, TaskStatus
from tasker.parse import detect_task_type
from tasker.repo import TaskRepo
from tasker.utils import JsonAppend, console

from ._common import app, get_task_repo, resolve_ref

_STATUS_COLOR = {
    TaskStatus.PENDING: "white",
    TaskStatus.IN_PROGRESS: "bright_blue",
    TaskStatus.DONE: "green",
    TaskStatus.CANCELLED: "bright_black",
}

_STATUS_MARKER = {
    TaskStatus.PENDING: r"\[ ]",
    TaskStatus.IN_PROGRESS: r"\[~]",
    TaskStatus.DONE: r"\[x]",
    TaskStatus.CANCELLED: r"\[x]",
}


@app.command("show", hidden=True)
@app.command("view", help="Print task content.")
def cmd_show_task(
    *,
    task_ref: Annotated[str, typer.Argument(help="Task ID to show.")],
    repo: TaskRepo = Depends(get_task_repo),
) -> None:
    with console.catching_output():
        task = resolve_ref(repo, task_ref, save_recent=True)

        color = _STATUS_COLOR[task.status]
        marker = _STATUS_MARKER[task.status]
        marker_prefix = ""
        if task.status != TaskStatus.PENDING:
            marker_prefix = f"[{color}]{marker}[/{color}] "

        console.print(
            f"[blue]{task.id}[/blue]: {marker_prefix}[bold]{task.title}[/bold]",
            json_output=_task_to_json(task),
        )

        if task.description:
            console.print(f"\n{task.description}")

        if task.extra_sections:
            console.print(f"\n{task.extra_sections}")

        if not task.subtasks:
            return

        console.print("\n[bold]Subtasks:[/bold]")
        for subtask in task.subtasks:
            sub_color = _STATUS_COLOR[subtask.status]
            sub_marker = _STATUS_MARKER[subtask.status]
            if subtask.status == TaskStatus.CANCELLED:
                line = f"{subtask.id}: {sub_marker} {subtask.title}"
                console.print(f"  - [{sub_color}]{line}[/{sub_color}]")
                continue

            sub_marker_prefix = ""
            if subtask.status != TaskStatus.PENDING:
                sub_marker_prefix = f"[{sub_color}]{sub_marker}[/{sub_color}] "

            console.print(
                f"  - [blue]{subtask.id}[/blue]: {sub_marker_prefix}{subtask.title}"
            )


@app.command("list", help="List open tasks with their pending subtasks.")
def cmd_list_tasks(
    *,
    task_refs: Annotated[
        list[str],
        typer.Argument(help="Task IDs to show (defaults to all root tasks)."),
    ] = [],
    show_all: Annotated[
        bool,
        typer.Option("--all", "-a", help="Show all subtasks including closed."),
    ] = False,
    repo: TaskRepo = Depends(get_task_repo),
) -> None:
    with console.catching_output():
        if task_refs:
            all_tasks = [resolve_ref(repo, ref, save_recent=True) for ref in task_refs]
        else:
            all_tasks = _load_root_tasks(repo)

        if not all_tasks:
            console.print("[dim]No tasks to show.[/dim]", json_output={"tasks": []})
            return

        for task in all_tasks:
            color = _STATUS_COLOR[task.status]
            marker = _STATUS_MARKER[task.status]

            marker_prefix = f"[{color}]{marker}[/{color}] "
            if task.status == TaskStatus.PENDING and not show_all:
                # note: when `--all` is used
                marker_prefix = ""

            console.print(
                f"[blue]{task.id}[/blue]: {marker_prefix}{task.title}",
                json_output={"tasks": JsonAppend(_task_to_json(task))},
            )

            _print_subtasks(task.subtasks, depth=1, show_all=show_all)


def _print_subtasks(subtasks: list[Task], *, depth: int, show_all: bool) -> None:
    indent = "  " * depth
    for task in subtasks:
        if not show_all and task.is_closed:
            continue

        color = _STATUS_COLOR[task.status]
        marker = _STATUS_MARKER[task.status]

        if task.status == TaskStatus.CANCELLED:
            line = f"{task.id}: {marker} {task.title}"
            console.print(f"{indent}- [{color}]{line}[/{color}]")
        else:
            marker_prefix = f"[{color}]{marker}[/{color}] "
            if not show_all and task.status == TaskStatus.PENDING:
                marker_prefix = ""

            console.print(
                f"{indent}- [blue]{task.id}[/blue]: {marker_prefix}{task.title}"
            )

        if task.subtasks:
            _print_subtasks(task.subtasks, depth=depth + 1, show_all=show_all)


def _load_root_tasks(repo: TaskRepo) -> list[Task]:
    tasks: list[Task] = []
    for task_path in repo.list_root_tasks():
        tp = detect_task_type(task_path)
        tasks.append(repo.resolve_ref(tp.task_ref))
    return tasks


def _task_to_json(task: Task) -> dict[str, Any]:
    return {
        "task_ref": task.ref,
        "id": task.id,
        "title": task.title,
        "status": task.status.value,
        "description": task.description,
        "subtasks": [
            {"id": s.id, "title": s.title, "status": s.status.value}
            for s in task.subtasks
        ],
    }
