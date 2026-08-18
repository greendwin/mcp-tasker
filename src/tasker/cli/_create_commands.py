import sys
from typing import Annotated, Optional

import typer
from typer_di import Depends

from tasker.repo import TaskRepo
from tasker.resolve import resolve_ref, save_recent_for_refs
from tasker.utils import console

from ._common import app, complete_task_ref, get_task_repo, unarchive_task
from ._helpers import edit_task_in_editor
from ._print_utils import print_parents_with_opened


@app.command("new", help="Create a new top-level task.")
def cmd_new_task(
    *,
    title: Annotated[str, typer.Argument(help="Task title.")],
    extra_words: Annotated[
        Optional[list[str]],
        typer.Argument(help="Additional title words.", metavar="WORDS"),
    ] = None,
    details: Annotated[
        Optional[str], typer.Option("--details", "-d", help="Task description.")
    ] = None,
    slug: Annotated[
        Optional[str], typer.Option("--slug", help="Override auto-derived slug.")
    ] = None,
    extended: Annotated[
        bool, typer.Option("--extended", help="Create task as a directory.")
    ] = False,
    editor: Annotated[
        bool,
        typer.Option("--editor", "-e", help="Open task file in editor after creating."),
    ] = False,
    repo: TaskRepo = Depends(get_task_repo),
) -> None:
    if extra_words:
        title = title + " " + " ".join(extra_words)

    task = repo.create_root_task(
        title=title, description=details, slug=slug, extended=extended
    )
    repo.flush_to_disk()

    if editor:
        edit_task_in_editor(repo, task)

    console.print(
        f"[green]Task [blue]{task.ref}[/blue] created[/green]",
        context={"task_ref": task.ref},
    )

    save_recent_for_refs(repo, task)
    print_parents_with_opened(repo, task)


@app.command("add", help="Add a subtask to an existing task.")
def cmd_add_task(
    *,
    parent_ref: Annotated[
        str, typer.Argument(help="Parent task ID.", autocompletion=complete_task_ref)
    ],
    title: Annotated[str, typer.Argument(help="Subtask title.")],
    extra_words: Annotated[
        Optional[list[str]],
        typer.Argument(help="Additional title words.", metavar="WORDS"),
    ] = None,
    details: Annotated[
        Optional[str], typer.Option("--details", "-d", help="Task description.")
    ] = None,
    slug: Annotated[
        Optional[str], typer.Option("--slug", help="Override auto-derived slug.")
    ] = None,
    editor: Annotated[
        bool,
        typer.Option("--editor", "-e", help="Open task file in editor after creating."),
    ] = False,
    repo: TaskRepo = Depends(get_task_repo),
) -> None:
    parent = resolve_ref(repo, parent_ref)
    unarchive_task(repo, parent.task)

    if extra_words:
        title = title + " " + " ".join(extra_words)

    child = repo.add_subtask(parent.task, title=title, description=details, slug=slug)
    repo.flush_to_disk()

    if editor:
        edit_task_in_editor(repo, child)

    console.print(
        f"[green]Task [blue]{child.ref}[/blue] added",
        context={"task_ref": child.ref},
    )

    save_recent_for_refs(repo, parent)
    print_parents_with_opened(repo, child)


@app.command("add-many", help="Interactively add multiple subtasks.")
def cmd_add_many_tasks(
    *,
    parent_ref: Annotated[
        str, typer.Argument(help="Parent task ID.", autocompletion=complete_task_ref)
    ],
    repo: TaskRepo = Depends(get_task_repo),
) -> None:
    parent = resolve_ref(repo, parent_ref)
    save_recent_for_refs(repo, parent)

    console.print(
        f"[cyan]Adding tasks to [blue]{parent.task_ref}[/blue][/cyan]"
        " (empty line to finish):",
        context={"parent_ref": parent_ref},
    )

    task_refs: list[str] = []
    while True:
        console.print("  [dim]>[/dim] ", end="")
        line = sys.stdin.readline()
        if not line or not line.strip():
            break
        child = repo.add_subtask(parent.task, title=line.strip())
        repo.flush_to_disk()
        task_refs.append(child.ref)
        console.print(f"  [green]task [blue]{child.ref}[/blue] added[/green]")

    if not task_refs:
        console.print(
            "[yellow]No tasks added[/yellow]",
            context={"task_refs": []},
        )
        return

    console.print(
        f"[green]Done:[/green] {len(task_refs)} task(s) added"
        f" to [blue]{parent.task.id}[/blue]",
        context={"task_refs": task_refs},
    )
