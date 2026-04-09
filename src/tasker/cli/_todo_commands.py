from typing import Annotated

import typer
from typer_di import Depends

from tasker.base_types import Task
from tasker.repo import TaskRepo
from tasker.resolve import resolve_ref, save_recent_for_refs
from tasker.todo import add_todo, remove_todo
from tasker.utils import JsonAppend, console

from ._common import app, complete_task_ref, get_task_repo
from ._print_utils import print_parent_preview


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
