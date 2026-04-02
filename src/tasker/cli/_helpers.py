import os
import platform
import subprocess
from pathlib import Path

from tasker.base_types import Task, TaskStatus
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
    highlight: bool = False,
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
    override_color: str | None = None

    if highlight:
        # override marker color
        override_color = "bright_yellow"
    elif task.status == TaskStatus.CANCELLED:
        override_color = _STATUS_COLOR[task.status]

    if override_color:
        r.append(f"[{override_color}]")

    if show_marker:
        r.append(_task_marker(task, colored=not override_color))
        r.append(" ")

    r.append(task.title)
    if override_color:
        r.append(f"[/{override_color}]")
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


def print_parent_preview(repo: TaskRepo, task: Task) -> None:
    ref = parse_task_ref(task.ref)
    parent = repo.resolve_ref(ref.parent_id)

    console.print("")
    console.print(format_task_list_item(parent))

    print_subtasks(
        parent.subtasks,
        show_all=False,
        highlight_id=task.id,
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
