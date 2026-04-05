import os
import platform
import subprocess
from collections import defaultdict
from pathlib import Path

from tasker.base_types import Task, TaskStatus, is_root_task_id
from tasker.parse import parse_task_ref
from tasker.repo._task_repo import TaskRepo
from tasker.utils import console

from ._resolve_task import load_recent_task_id

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
    highlight_ids: set[str] | None = None,
    recent_id: str | None = None,
    show_subtask_count: bool = False,
) -> str:
    r = []

    if indent > 0:
        r.append("  " * indent)
        r.append("- ")

    id_color = "blue"
    if task.deleted:
        id_color = "red"
    elif task.status in (TaskStatus.CANCELLED, TaskStatus.IN_PROGRESS):
        # override task_id by status collor
        id_color = _STATUS_COLOR[task.status]

    if show_task_id:
        r.append(f"[{id_color}]")
        r.append(task.id)
        r.append(f"[/{id_color}]")
        r.append(": ")

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

    if show_subtask_count:
        total = _count_subtasks(task)
        if total > 0:
            r.append(f" [dim](+{total} subtasks)[/dim]")

    if highlight_ids and task.id in highlight_ids:
        r.append(" [bright_yellow]<<<[/bright_yellow]")

    if recent_id and task.id == recent_id:
        r.append(" [cyan](q)[/cyan]")

    return "".join(r)


def _count_subtasks(task: Task) -> int:
    count = len(task.subtasks)
    for child in task.subtasks:
        if child.subtasks:
            count += _count_subtasks(child)
    return count


def print_subtasks(
    subtasks: list[Task],
    *,
    current_depth: int = 1,
    show_all: bool,
    highlight_ids: set[str] | None = None,
    recent_id: str | None = None,
) -> None:
    for task in subtasks:
        if task.is_closed and not show_all:
            if not _has_highlights(task, highlight_ids):
                continue

        console.print(
            format_task_list_item(
                task,
                indent=current_depth,
                show_all=show_all,
                highlight_ids=highlight_ids,
                recent_id=recent_id,
            )
        )

        if task.subtasks:
            print_subtasks(
                task.subtasks,
                current_depth=current_depth + 1,
                show_all=show_all,
                highlight_ids=highlight_ids,
                recent_id=recent_id,
            )


def _has_highlights(task: Task, highlight_ids: set[str] | None) -> bool:
    if not highlight_ids:
        return False

    if task.id in highlight_ids:
        return True

    for child in task.subtasks:
        if _has_highlights(child, highlight_ids):
            return True

    return False


def print_parent_preview(repo: TaskRepo, *tasks: Task) -> None:
    if not tasks:
        return

    recent_id = load_recent_task_id(repo)

    # group tasks by root story, then find common ancestor per group
    root_groups: dict[str, list[Task]] = defaultdict(list)
    for task in tasks:
        ref = parse_task_ref(task.ref)
        root_groups[ref.root_id].append(task)

    console.print("")

    for group in root_groups.values():
        ids = {t.id for t in group}

        # collect parent IDs (direct parent or self for root tasks)
        parent_ids: list[str] = []
        for task in group:
            if is_root_task_id(task.id):
                parent_ids.append(task.id)
                continue

            ref = parse_task_ref(task.ref)
            parent_ids.append(ref.parent_id)

        common_id = _find_common_ancestor(parent_ids)
        parent = repo.resolve_ref(common_id)

        console.print(
            format_task_list_item(
                parent,
                highlight_ids=ids,
                recent_id=recent_id,
            )
        )

        print_subtasks(
            parent.subtasks,
            show_all=False,
            highlight_ids=ids,
            recent_id=recent_id,
        )


def _find_common_ancestor(parent_ids: list[str]) -> str:
    chains = [_get_ancestor_chain(pid) for pid in parent_ids]
    common = chains[0][0]  # root — always shared
    for depth in range(min(len(c) for c in chains)):
        if all(c[depth] == chains[0][depth] for c in chains):
            common = chains[0][depth]
        else:
            break

    return common


def _get_ancestor_chain(task_id: str) -> list[str]:
    chain = [task_id]
    current = task_id
    while not is_root_task_id(current):
        ref = parse_task_ref(current)
        current = ref.parent_id
        chain.append(current)
    chain.reverse()
    return chain


def edit_task_in_editor(repo: TaskRepo, task: Task) -> Task:
    # make sure that task is not inline
    if task.is_inline:
        repo.upgrade_to_filebased(task)

    # flush to ensure filename matches current slug
    # (slug may have been changed externally or via --slug)
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
