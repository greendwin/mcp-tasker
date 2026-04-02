import os
import platform
import subprocess
from pathlib import Path

from tasker.base_types import Task, TaskStatus
from tasker.repo._task_repo import TaskRepo
from tasker.utils import console

_STATUS_COLOR = {
    TaskStatus.PENDING: "white",
    TaskStatus.IN_PROGRESS: "bright_blue",
    TaskStatus.DONE: "green",
    TaskStatus.CANCELLED: "bright_black",
}

_STATUS_MARKER = {
    TaskStatus.PENDING: r"\[ ]",
    TaskStatus.IN_PROGRESS: r"\[~]",
    TaskStatus.DONE: r"\[x]",
    TaskStatus.CANCELLED: r"\[x]",
}


def _task_id(task: Task) -> str:
    return f"[blue]{task.id}[/blue]"


def _task_marker(task: Task, *, colored: bool) -> str:
    if not colored:
        return _STATUS_MARKER[task.status]

    color = _STATUS_COLOR[task.status]
    marker = _STATUS_MARKER[task.status]
    return f"[{color}]{marker}[/{color}]"


def format_task_list_item(
    task: Task,
    *,
    show_all: bool = False,
    indent: int = 0,
    highlight: bool = False,
) -> str:
    prefix = ""
    if indent > 0:
        prefix = "  " * indent + "- "

    # note: omit `[ ]` for pending tasks unless when `--all` is used
    omit_marker = not show_all and task.status == TaskStatus.PENDING

    if highlight:
        if omit_marker:
            return (
                f"{prefix}{_task_id(task)}: [bright_yellow]{task.title}[/bright_yellow]"
            )

        marker = _task_marker(task, colored=False)
        return f"{prefix}{_task_id(task)}: [bright_yellow]{marker} {task.title}[/bright_yellow]"

    if omit_marker:
        return f"{prefix}{_task_id(task)}: {task.title}"

    if task.status == TaskStatus.CANCELLED:
        color = _STATUS_COLOR[task.status]
        marker = _task_marker(task, colored=False)
        return f"{prefix}[{color}]{task.id}: {marker} {task.title}[/{color}]"

    marker = _task_marker(task, colored=True)
    return f"{prefix}{_task_id(task)}: {marker} {task.title}"


def print_subtasks(
    subtasks: list[Task],
    *,
    current_depth: int = 1,
    show_all: bool,
    highlight_id: str | None = None,
) -> None:
    for task in subtasks:
        if task.is_closed and not show_all and task.id != highlight_id:
            # skip closed task unless `--all` is used or task is highlighted
            continue

        console.print(
            format_task_list_item(
                task,
                indent=current_depth,
                show_all=show_all,
                highlight=task.id == highlight_id,
            )
        )

        if task.subtasks:
            print_subtasks(
                task.subtasks,
                current_depth=current_depth + 1,
                show_all=show_all,
                highlight_id=highlight_id,
            )


def edit_task_in_editor(repo: TaskRepo, task: Task) -> None:
    # make sure that task is not inline
    if task.is_inline:
        repo.upgrade_to_filebased(task)
        repo.flush_to_disk()

    task_path = repo.build_task_path(task)
    run_editor(task_path.resolve())

    # after edit many things can be changed including `slug`
    # if so - reload full tree and flush it back
    reload = TaskRepo(repo.root)
    _ = reload.resolve_ref(task.ref)
    reload.flush_to_disk()


def run_editor(path: Path) -> None:
    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR")
    if not editor:
        editor = "notepad" if platform.system() == "Windows" else "vi"

    subprocess.run([editor, str(path)])
