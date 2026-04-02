from typing import Annotated, Any

import typer
from typer_di import Depends

from tasker.base_types import Task, TaskStatus
from tasker.parse import detect_task_type
from tasker.repo import TaskRepo
from tasker.utils import JsonAppend, console

from ._common import app, get_task_repo
from ._helpers import format_task_list_item, print_subtasks
from ._resolve_task import resolve_ref


@app.command("show", hidden=True)
@app.command("view", help="Print task content.")
def cmd_show_task(
    *,
    task_ref: Annotated[str, typer.Argument(help="Task ID to show.")],
    repo: TaskRepo = Depends(get_task_repo),
) -> None:
    with console.catching_output():
        task = resolve_ref(repo, task_ref, save_recent=True)

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
            console.print(format_task_list_item(subtask, indent=1))


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
            console.print(
                format_task_list_item(task, show_all=show_all),
                json_output={"tasks": JsonAppend(_task_to_json(task))},
            )

            print_subtasks(task.subtasks, show_all=show_all)


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
