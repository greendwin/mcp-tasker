from typing import Annotated

import typer
from typer_di import Depends

from tasker.base_types import Task
from tasker.repo import TaskRepo, list_open_leaf_tasks
from tasker.resolve import (
    resolve_user_refs,
    save_recent_for_refs,
    to_tasks,
)
from tasker.todo import load_todo_list, resolve_todo_tasks, save_todo_list
from tasker.utils import console

from ._common import app, complete_task_ref, get_task_repo
from ._print_utils import (
    ActionReportConfig,
    print_action_report,
    print_parents_only,
    print_parents_with_opened,
)


@app.command("todo", help="Add task(s) to the TODO list.")
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
    resolved = resolve_user_refs(repo, task_refs)
    todo = load_todo_list(repo)

    report = ActionReportConfig()
    for _, task in resolved:
        console.append_context("task_refs", task.id)

        p = report.add_task(task)

        if task.id in todo:
            p.outcome = "already in todo"
            continue

        todo.append(task.id)

    print_action_report("Adding to TODO", report)
    save_todo_list(repo, todo)
    save_recent_for_refs(repo, *resolved)

    print_parents_only(
        repo,
        *resolve_todo_tasks(repo, todo),
        highlight={p.task.id for p in resolved},
    )


@app.command("untodo", help="Remove task(s) from the TODO list.")
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
    resolved = resolve_user_refs(repo, task_refs)
    tasks = to_tasks(resolved)
    todo = load_todo_list(repo)

    report = ActionReportConfig()
    items = {}
    for task in tasks:
        p = items[task.id] = report.add_task(task)
        console.append_context("task_refs", task.id)

        if task.id not in todo:
            p.outcome = "was not in todo"
        else:
            todo.remove(task.id)

    # check for tasks that remain in todo due to parents
    for task in tasks:
        if _check_under_todo_ancestor(repo, task, todo):
            items[task.id].outcome = "still in todo via parent"

    print_action_report("Removing from TODO", report)
    save_recent_for_refs(repo, *resolved)
    save_todo_list(repo, todo)

    if not todo:
        console.print("[yellow]Todo list is empty.[/yellow]")
        opened_tasks = list_open_leaf_tasks(repo)
        print_parents_with_opened(
            repo,
            *opened_tasks,
            *tasks,
            highlight={p.id for p in tasks},
        )
        return

    print_parents_only(
        repo,
        *resolve_todo_tasks(repo, todo),
        *tasks,
        highlight={p.id for p in tasks},
    )


def _check_under_todo_ancestor(repo: TaskRepo, task: Task, todo: list[str]) -> bool:
    cur = task
    while parent := repo.get_parent(cur):
        if parent.id in todo:
            return True
        cur = parent

    return False
