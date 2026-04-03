import sys
from typing import Annotated, Optional

import typer
from typer_di import Depends

from tasker.repo import TaskRepo
from tasker.utils import console

from ._common import app, get_task_repo
from ._helpers import edit_task_in_editor, print_parent_preview
from ._resolve_task import resolve_ref, save_recent_task


@app.command("new", help="Create a new top-level task.")
@console.catching_output
def cmd_new_task(
    *,
    title: Annotated[str, typer.Argument(help="Task title.")],
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
    task = repo.create_root_task(
        title=title, description=details, slug=slug, extended=extended
    )
    repo.flush_to_disk()
    save_recent_task(repo, task.id)

    if editor:
        task = edit_task_in_editor(repo, task)

    console.print(
        f"[green]Task [blue]{task.ref}[/blue] created[/green]",
        json_output={"task_ref": task.ref},
    )

    print_parent_preview(repo, task)


@app.command("add", help="Add a subtask to an existing task.")
@console.catching_output
def cmd_add_task(
    *,
    parent_ref: Annotated[str, typer.Argument(help="Parent task ID.")],
    title: Annotated[str, typer.Argument(help="Subtask title.")],
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
    parent = resolve_ref(repo, parent_ref, save_recent=True, auto_unarchive=True)
    child = repo.add_subtask(parent, title=title, description=details, slug=slug)
    repo.flush_to_disk()

    if editor:
        child = edit_task_in_editor(repo, child)

    console.print(
        f"[green]Task [blue]{child.ref}[/blue] added",
        json_output={"task_ref": child.ref},
    )

    print_parent_preview(repo, child)


@app.command("add-many", help="Interactively add multiple subtasks.")
@console.catching_output
def cmd_add_many_tasks(
    *,
    parent_ref: Annotated[str, typer.Argument(help="Parent task ID.")],
    repo: TaskRepo = Depends(get_task_repo),
) -> None:
    parent = resolve_ref(repo, parent_ref, save_recent=True)

    console.print(
        f"[cyan]Adding tasks to [blue]{parent.ref}[/blue][/cyan]"
        " (empty line to finish):",
        json_output={"parent_ref": parent_ref},
    )

    task_refs: list[str] = []
    while True:
        console.print("  [dim]>[/dim] ", end="")
        line = sys.stdin.readline()
        if not line or not line.strip():
            break
        child = repo.add_subtask(parent, title=line.strip())
        repo.flush_to_disk()
        task_refs.append(child.ref)
        console.print(f"  [green]task [blue]{child.ref}[/blue] added[/green]")

    if not task_refs:
        console.print(
            "[yellow]No tasks added[/yellow]",
            json_output={"task_refs": []},
        )
        return

    console.print(
        f"[green]Done:[/green] {len(task_refs)} task(s) added"
        f" to [blue]{parent.id}[/blue]",
        json_output={"task_refs": task_refs},
    )
