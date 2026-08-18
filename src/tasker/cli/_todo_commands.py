from typing import Annotated

import typer
from typer_di import Depends

from tasker.base_types import Task
from tasker.repo import TaskRepo
from tasker.resolve import resolve_ref, save_recent_for_refs
from tasker.todo import load_todo_ids, remove_todo, save_todo_ids
from tasker.utils import JsonAppend, console

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
    assert task_refs  # sanity check
    resolved = [resolve_ref(repo, ref) for ref in task_refs]
    todo_list = load_todo_ids(repo)

    report = ActionReportConfig()
    for _, task in resolved:
        console.append_context("task_refs", task.id)

        if task.id in todo_list:
            report.add_task(task, outcome="already in todo")
            continue

        report.add_task(task)
        todo_list.append(task.id)

    print_action_report("Adding to TODO", report)

    save_todo_ids(repo, todo_list)
    save_recent_for_refs(repo, *resolved)

    # TODO: this list could be outdated, some of refs could be unavailable
    todo_tasks = [repo.resolve_ref(ref) for ref in todo_list]
    print_parents_only(repo, *todo_tasks, highlight={p.task.id for p in resolved})


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
    resolved = [resolve_ref(repo, ref) for ref in task_refs]

    need_preview: list[Task] = []
    for _, task in resolved:
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

    save_recent_for_refs(repo, *resolved)
    print_parents_with_opened(repo, *need_preview)
