import re
from typing import NamedTuple

from tasker.base_types import Task
from tasker.exceptions import TaskValidateError
from tasker.parse import find_common_ancestor, make_child_ref, parse_task_ref
from tasker.repo._task_repo import TaskRepo
from tasker.utils import JsonAppend, console, write_text

_RECENT_FILE = ".recent"


class ResolvedRef(NamedTuple):
    task_ref: str  # original task ref, could be recent link aka `qNN`
    task: Task  # resolved task


def resolve_ref(
    repo: TaskRepo,
    task_ref: str,
) -> ResolvedRef:
    if _is_direct_ref(task_ref):
        resolved_ref = task_ref
    else:
        resolved_ref = _resolve_recent(repo, task_ref)

    resolved_task = repo.resolve_ref(resolved_ref)

    return ResolvedRef(task_ref, resolved_task)


def unarchive_task(repo: TaskRepo, task: Task) -> bool:
    if not task.archived:
        return False

    ref = parse_task_ref(task.id)
    root_task = repo.resolve_ref(ref.root_id)

    root_task.archived = False
    _set_archived_recursive(root_task)
    repo.flush_to_disk()

    console.print(
        f"[yellow]Unarchiving [blue]{root_task.ref}[/blue] automatically[/yellow]",
        json_output={"unarchived_ref": JsonAppend(ref.root_id)},
    )
    return True


def _set_archived_recursive(task: Task) -> None:
    task.archived = False
    for child in task.subtasks:
        _set_archived_recursive(child)


def _is_direct_ref(task_ref: str) -> bool:
    return task_ref.startswith("s")


def save_recent_for_refs(repo: TaskRepo, *refs: ResolvedRef | Task) -> None:
    # collect id of tasks that were resolved from direct refs
    direct_refs: list[str] = []
    for p in refs:
        if isinstance(p, Task):
            direct_refs.append(p.id)
        elif _is_direct_ref(p.task_ref):
            direct_refs.append(p.task.id)

    if not direct_refs:
        return

    task_id = find_common_ancestor(direct_refs)

    # save recent
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
