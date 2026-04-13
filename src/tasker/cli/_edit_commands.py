from typing import Annotated

import typer
from typer_di import Depends

from tasker.repo import TaskRepo
from tasker.resolve import (
    ResolvedRef,
    resolve_ref,
    save_recent_for_refs,
)
from tasker.utils import console

from ._common import app, complete_task_ref, get_task_repo
from ._helpers import edit_task_in_editor
from ._print_utils import compute_markers, print_task


@app.command("edit", help="Edit task properties (title, details, slug).")
def cmd_edit_task(
    *,
    task_ref: Annotated[
        str, typer.Argument(help="Task ID to edit.", autocompletion=complete_task_ref)
    ],
    title: Annotated[
        str | None,
        typer.Option("--title", "-t", help="New task title."),
    ] = None,
    details: Annotated[
        str | None,
        typer.Option("--details", "-d", help="New task description."),
    ] = None,
    slug: Annotated[
        str | None,
        typer.Option("--slug", "-s", help="New task slug."),
    ] = None,
    editor: Annotated[
        bool,
        typer.Option(
            "--editor", "-e", help="Open task file in editor after applying changes."
        ),
    ] = False,
    repo: TaskRepo = Depends(get_task_repo),
) -> None:
    if not editor and title is None and details is None and slug is None:
        if not console.json_output:
            # open editor by default
            editor = True
        else:
            # but not in json-output mode
            console.print(
                "[red]Error:[/red] At least one of"
                " --title, --details, --slug, or --editor is required.",
                context={"error": "No fields to edit."},
            )
            raise typer.Exit(1)

    resolved = resolve_ref(repo, task_ref)

    if title is not None or details is not None or slug is not None:
        repo.edit_task(resolved.task, title=title, description=details, slug=slug)
        repo.flush_to_disk()

    if editor:
        edited = edit_task_in_editor(repo, resolved.task)
        resolved = ResolvedRef(resolved.task_ref, edited)

    console.print(
        f"[green]Task [blue]{resolved.task.ref}[/blue] updated[/green]",
        context={"task_ref": resolved.task.ref},
    )

    save_recent_for_refs(repo, resolved)

    markers = compute_markers(repo, resolved.task)
    print_task(resolved.task, markers=markers, preview=True)
