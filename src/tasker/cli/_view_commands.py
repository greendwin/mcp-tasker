from typing import Annotated, Any

import typer
from typer_di import Depends

from tasker.base_types import Task
from tasker.parse import detect_task_type, parse_task_file
from tasker.repo import TaskRepo
from tasker.resolve import ResolvedRef, resolve_ref, save_recent_for_refs
from tasker.todo import load_todo_ids
from tasker.utils import console

from ._common import app, complete_task_ref, get_task_repo
from ._print_utils import compute_markers, print_task, print_tree


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

    _, task = resolved

    save_recent_for_refs(repo, resolved)

    # note compute markers *after* recent was updated to show actual info
    markers = compute_markers(repo, task, *task.subtasks)

    print_task(task, markers=markers, preview=False)
    console.set_context("task", _task_to_json(task))


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
    todo: Annotated[
        bool,
        typer.Option("--todo", help="Show only tasks from the TODO list."),
    ] = False,
    repo: TaskRepo = Depends(get_task_repo),
) -> None:
    show_tasks: list[Task] = []

    if todo:
        todo_ids = load_todo_ids(repo)
        for task_id in sorted(todo_ids):
            show_tasks.append(repo.resolve_ref(task_id))

    if archived:
        show_tasks.extend(_load_root_tasks(repo, archived=True, shallow=not show_all))
    elif not todo and not task_refs:
        show_tasks.extend(_load_root_tasks(repo, archived=False, shallow=False))

    resolved: list[ResolvedRef] = []
    for ref in task_refs:
        r = resolve_ref(repo, ref)
        show_tasks.append(r.task)
        resolved.append(r)

    save_recent_for_refs(repo, *resolved)

    if not show_tasks:
        console.print("[dim]No tasks to show.[/dim]", context={"tasks": []})
        return

    print_tree(repo, show_tasks=show_tasks, show_all=show_all)

    for task in show_tasks:
        console.append_context("tasks", _task_to_json(task))


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
