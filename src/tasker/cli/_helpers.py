import os
import platform
import subprocess
from pathlib import Path

from tasker.base_types import Task, TaskStatus, is_root_task_id
from tasker.parse import parse_task_ref
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


def _task_marker(task: Task, *, colored: bool) -> str:
    if not colored:
        return _STATUS_MARKER[task.status]

    color = _STATUS_COLOR[task.status]
    marker = _STATUS_MARKER[task.status]
    return f"[{color}]{marker}[/{color}]"


def format_task_list_item(
    task: Task,
    *,
    show_task_id: bool = True,
    show_all: bool = False,
    indent: int = 0,
    highlight_id: str | None = None,
) -> str:
    r = []

    if indent > 0:
        r.append("  " * indent)
        r.append("- ")

    id_color = "blue"
    if task.status in (TaskStatus.CANCELLED, TaskStatus.IN_PROGRESS):
        # override task_id by status collor
        id_color = _STATUS_COLOR[task.status]

    if show_task_id:
        r.append(f"[{id_color}]")
        r.append(task.id)
        r.append(": ")
        r.append(f"[/{id_color}]")

    # note: omit `[ ]` for pending tasks unless when `--all` is used
    show_marker = show_all or task.status != TaskStatus.PENDING

    color_override: str | None = None
    if task.status == TaskStatus.CANCELLED:
        color_override = _STATUS_COLOR[task.status]

    if color_override:
        r.append(f"[{color_override}]")

    if show_marker:
        r.append(_task_marker(task, colored=not color_override))
        r.append(" ")

    r.append(task.title)

    if color_override:
        r.append(f"[/{color_override}]")

    if task.id == highlight_id:
        r.append(" [bright_yellow]<<<[/bright_yellow]")

    return "".join(r)


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
                highlight_id=highlight_id,
            )
        )

        if task.subtasks:
            print_subtasks(
                task.subtasks,
                current_depth=current_depth + 1,
                show_all=show_all,
                highlight_id=highlight_id,
            )


def print_parent_preview(repo: TaskRepo, task: Task) -> None:
    if is_root_task_id(task.id):
        # show task itself
        parent = task
    else:
        ref = parse_task_ref(task.ref)
        parent = repo.resolve_ref(ref.parent_id)

    console.print("")
    console.print(format_task_list_item(parent, highlight_id=task.id))

    print_subtasks(
        parent.subtasks,
        show_all=False,
        highlight_id=task.id,
    )


def edit_task_in_editor(repo: TaskRepo, task: Task) -> Task:
    # make sure that task is not inline
    if task.is_inline:
        repo.upgrade_to_filebased(task)
        repo.flush_to_disk()

    task_path = repo.build_task_path(task)
    run_editor(task_path.resolve())

    # after edit many things can be changed including `slug`
    # if so - reload full tree and flush it back
    reload = TaskRepo(repo.root)
    updated = reload.resolve_ref(task.id)
    reload.flush_to_disk()
    return updated


def run_editor(path: Path) -> None:
    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR")
    if not editor:
        editor = "notepad" if platform.system() == "Windows" else "vi"

    subprocess.run([editor, str(path)])
