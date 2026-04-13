from typing import Annotated, Any

import typer
from typer_di import Depends

from tasker.base_types import Task
from tasker.parse import detect_task_type, parse_task_file
from tasker.repo import TaskRepo
from tasker.resolve import (
    ResolvedRef,
    load_closed_tasks,
    resolve_ref,
    save_recent_for_refs,
)
from tasker.todo import load_todo_tasks
from tasker.utils import console

from ._common import app, complete_task_ref, get_task_repo
from ._print_utils import (
    ShowChildrenMode,
    ShowTaskConfig,
    compute_markers,
    print_task,
    print_tree,
)

DEFAULT_CLOSED_LIMIT = 5


@app.command("show", hidden=True)
@app.command("view", help="Print task content.")
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
    closed: Annotated[
        bool,
        typer.Option(
            "--closed",
            help=(
                f"Show up to {DEFAULT_CLOSED_LIMIT} recently closed tasks."
                " Mutually exclusive with --archived, --todo, and task refs."
            ),
        ),
    ] = False,
    repo: TaskRepo = Depends(get_task_repo),
) -> None:
    if todo and archived:
        raise typer.BadParameter("--todo and --archived cannot be used together")
    if closed and (archived or todo or task_refs):
        raise typer.BadParameter(
            "--closed cannot be combined with --archived, --todo, or task refs"
        )

    tasks: list[Task] = []

    if closed:
        tasks.extend(load_closed_tasks(repo, limit=DEFAULT_CLOSED_LIMIT))
    elif todo:
        tasks.extend(load_todo_tasks(repo))

    if archived:
        tasks.extend(_load_root_tasks(repo, archived=True, shallow=not show_all))
    elif not closed and not todo and not task_refs:
        tasks.extend(_load_root_tasks(repo, archived=False, shallow=False))

    resolved: list[ResolvedRef] = []
    for ref in task_refs:
        r = resolve_ref(repo, ref)
        tasks.append(r.task)
        resolved.append(r)

    save_recent_for_refs(repo, *resolved)

    if not tasks:
        console.print("[dim]No tasks to show.[/dim]", context={"tasks": []})
        return

    show_children_mode = ShowChildrenMode.SHOW_OPENED
    if show_all:
        show_children_mode = ShowChildrenMode.SHOW_ALL

    config = ShowTaskConfig(
        show_task_id=True,
        show_pending_marker=show_all,
    )

    for task in tasks:
        config.show_task(
            task,
            show_children_mode=show_children_mode,
        )

        if parent := repo.get_parent(task):
            # note: no children mode for parent, just show the parent node
            config.show_task(parent)

    print_tree(repo, config)

    for task in tasks:
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
