from __future__ import annotations

from tasker import git
from tasker.base_types import EXTENDED_TASK_FILENAME
from tasker.exceptions import TaskValidateError
from tasker.layout import discover_tasker_dir
from tasker.merge import merge_task_file
from tasker.parse import detect_task_type
from tasker.utils import console, write_text

from ._common import app


@app.command("resolve", help="Auto-merge conflicted task files after a git merge.")
def cmd_resolve() -> None:
    tasker_dir = discover_tasker_dir()
    repo_root = tasker_dir.parent

    conflicts = git.list_conflicted_files(tasker_dir, repo_root=repo_root)

    if not conflicts:
        console.print("[green]No conflicts found[/green]")
        return

    resolved_count = 0
    conflict_count = 0
    skipped_count = 0

    for cf in conflicts:
        file_path = repo_root / cf.path

        # For extended tasks the conflicted path is the README.md inside the
        # task directory; detect_task_type expects the directory itself.
        if file_path.name == EXTENDED_TASK_FILENAME:
            task_path = file_path.parent
        else:
            task_path = file_path

        try:
            detect_result = detect_task_type(task_path)
        except TaskValidateError:
            detect_result = None

        if detect_result is None:
            console.print(f"[yellow]Skipping unrecognised file: {cf.path}[/yellow]")
            skipped_count += 1
            continue

        if cf.ours is None or cf.theirs is None:
            console.print(
                f"[yellow]Skipping file with missing side: {cf.path}[/yellow]"
            )
            skipped_count += 1
            continue

        try:
            result = merge_task_file(
                cf.base,
                cf.ours,
                cf.theirs,
                task_id=detect_result.task_id,
                slug=detect_result.slug,
                extended=detect_result.extended,
            )
        except Exception as ex:
            if console.debug:
                console.print_exception()

            console.print(
                f"[yellow]Skipping file with merge error: {cf.path} ({ex})[/yellow]"
            )
            skipped_count += 1
            continue

        write_text(detect_result.content_path, result.content)

        if result.has_conflicts:
            conflict_count += 1
            console.print(f"[yellow]Conflict remains: {cf.path}[/yellow]")
        else:
            resolved_count += 1
            git.stage_file(cf.path, repo_root=repo_root)
            console.print(f"[green]Resolved: {cf.path}[/green]")

    parts: list[str] = []
    if resolved_count:
        parts.append(f"{resolved_count} resolved")
    if conflict_count:
        parts.append(f"{conflict_count} conflict(s) remaining")
    if skipped_count:
        parts.append(f"{skipped_count} skipped")

    console.print(", ".join(parts))
