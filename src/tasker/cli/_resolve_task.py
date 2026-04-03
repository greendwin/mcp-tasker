import re

import typer

from tasker.base_types import Task
from tasker.exceptions import TaskArchivedError, TaskValidateError
from tasker.parse import make_child_ref, parse_task_ref
from tasker.repo._task_repo import TaskRepo
from tasker.utils import JsonAppend, console, write_text

_RECENT_FILE = ".recent"


def resolve_ref(
    repo: TaskRepo,
    task_ref: str,
    *,
    save_recent: bool = False,
    auto_unarchive: bool = False,
) -> Task:
    is_direct_link = task_ref.startswith("s")
    if not is_direct_link:
        task_ref = _resolve_recent(repo, task_ref)

    if auto_unarchive and repo.is_archived_task(task_ref):
        ref = parse_task_ref(task_ref)
        repo.unarchive_root_task(ref.root_id)
        root = repo.resolve_ref(ref.root_id)
        console.print(
            f"[yellow]Unarchiving [blue]{root.ref}[/blue] automatically[/yellow]",
            json_output={"unarchived_ref": JsonAppend(ref.root_id)},
        )

    try:
        task = repo.resolve_ref(task_ref)
    except TaskArchivedError as ex:
        if console.json_output:
            raise

        console.print(f"[yellow]Task [blue]{ex.task_ref}[/blue] is archived[/yellow]")
        console.print("Unarchive it first before performing actions on it")
        raise typer.Exit(1) from ex

    if save_recent and is_direct_link:
        save_recent_task(repo, task.id)

    return task


def save_recent_task(repo: TaskRepo, task_id: str) -> None:
    write_text(repo.root / _RECENT_FILE, task_id + "\n")


def load_recent_task_id(repo: TaskRepo) -> str | None:
    path = repo.root / _RECENT_FILE
    if not path.exists():
        return None

    text = path.read_text().strip()
    return text or None


def _resolve_recent(repo: TaskRepo, task_ref: str) -> str:
    if not task_ref.startswith(("p", "q")):
        # resolve as-is, try to resolve in repo
        return task_ref

    recent_ref = _load_recent(repo, task_ref)

    if task_ref == "q":
        return recent_ref

    # links like q0102
    if m := re.fullmatch(r"q((?:\d{2})+)", task_ref):
        return make_child_ref(recent_ref, m.group(1))

    # links like p, p01, pp, pp0102
    if m := re.fullmatch(r"(p+)((?:\d{2})+)?", task_ref):
        ancestor_id = recent_ref
        for _ in range(len(m.group(1))):
            ancestor_id = parse_task_ref(ancestor_id).parent_id
        digits = m.group(2)

        if digits:
            return make_child_ref(ancestor_id, digits)
        return ancestor_id

    raise TaskValidateError(f"Invalid recent reference {task_ref!r}", task_ref=task_ref)


def _load_recent(repo: TaskRepo, task_ref: str) -> str:
    path = repo.root / _RECENT_FILE
    if not path.exists():
        raise TaskValidateError("Recent task was not set yet", task_ref=task_ref)

    text = path.read_text().strip()
    if not text:
        raise TaskValidateError("Recent task was not set yet", task_ref=task_ref)

    return text
