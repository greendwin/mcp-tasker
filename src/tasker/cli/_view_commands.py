from typing import Annotated, Any

import typer
from typer_di import Depends

from tasker.base_types import Task
from tasker.parse import detect_task_type, parse_task_file
from tasker.repo import TaskRepo
from tasker.utils import JsonAppend, console

from ._common import app, complete_task_ref, get_task_repo
from ._helpers import format_task_list_item, print_subtasks
from ._resolve_task import (
    ResolvedRef,
    load_recent_task_id,
    resolve_ref,
    save_recent_for_refs,
)


@app.command("show", hidden=True)
@app.command("view", help="Print task content.")
@console.catching_output
def cmd_show_task(
    *,
    task_ref: Annotated[
        str, typer.Argument(help="Task ID to show.", autocompletion=complete_task_ref)
    ],
    repo: TaskRepo = Depends(get_task_repo),
) -> None:
    resolved = resolve_ref(repo, task_ref)
    save_recent_for_refs(repo, resolved)

    _, task = resolved

    console.print(
        format_task_list_item(task),
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
        console.print(format_task_list_item(subtask, indent=1, show_subtask_count=True))


@app.command("list", help="List open tasks with their pending subtasks.")
@console.catching_output
def cmd_list_tasks(
    *,
    task_refs: Annotated[
        list[str],
        typer.Argument(
            help="Task IDs to show (defaults to all root tasks).",
            autocompletion=complete_task_ref,
        ),
    ] = [],
    show_all: Annotated[
        bool,
        typer.Option("--all", "-a", help="Show all subtasks including closed."),
    ] = False,
    archived: Annotated[
        bool,
        typer.Option(
            "--archived", "--arch", help="List archived tasks instead of active ones."
        ),
    ] = False,
    repo: TaskRepo = Depends(get_task_repo),
) -> None:
    if archived:
        all_tasks = _load_root_tasks(repo, archived=True, shallow=not show_all)
    elif not task_refs:
        all_tasks = _load_root_tasks(repo, archived=False, shallow=False)
    else:
        all_tasks = []

    resolved: list[ResolvedRef] = []
    for ref in task_refs:
        r = resolve_ref(repo, ref)
        all_tasks.append(r.task)
        resolved.append(r)

    save_recent_for_refs(repo, *resolved)

    if not all_tasks:
        console.print("[dim]No tasks to show.[/dim]", json_output={"tasks": []})
        return

    recent_id = load_recent_task_id(repo)

    for task in all_tasks:
        console.print(
            format_task_list_item(task, show_all=show_all, recent_id=recent_id),
            json_output={"tasks": JsonAppend(_task_to_json(task))},
        )

        print_subtasks(task.subtasks, show_all=show_all, recent_id=recent_id)


def _load_root_tasks(repo: TaskRepo, *, shallow: bool, archived: bool) -> list[Task]:
    tasks: list[Task] = []
    for task_path in repo.list_root_tasks(archived=archived):
        if shallow:
            task, _ = parse_task_file(task_path)
            tasks.append(task)
            continue

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
