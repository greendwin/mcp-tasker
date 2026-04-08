import json
import re
from enum import Enum
from typing import NamedTuple

from .base_types import Task
from .exceptions import TaskValidateError
from .layout import RECENT_FILE
from .parse import find_common_ancestor, make_child_ref, parse_task_ref
from .repo import TaskRepo
from .utils import write_text


class ResolvedRef(NamedTuple):
    task_ref: str  # original task ref, could be recent link aka `qNN`
    task: Task  # resolved task


class RecentData(NamedTuple):
    recent: str | None
    closed: list[str]


class _Keep(Enum):
    KEEP = "keep"


_KEEP = _Keep.KEEP


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


def _is_direct_ref(task_ref: str) -> bool:
    return task_ref.startswith("s")


def _load_recent_data(repo: TaskRepo) -> RecentData:
    path = repo.root / RECENT_FILE
    if not path.exists():
        return RecentData(recent=None, closed=[])

    text = path.read_text().strip()
    if not text:
        return RecentData(recent=None, closed=[])

    if text.startswith("{"):
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return RecentData(recent=None, closed=[])
        return RecentData(
            recent=data.get("recent"),
            closed=data.get("closed", []),
        )

    # legacy plain-text format
    return RecentData(recent=text, closed=[])


def _update_recent_data(
    repo: TaskRepo,
    *,
    recent: str | None | _Keep = _KEEP,
    closed: list[str] | _Keep = _KEEP,
) -> None:
    data = _load_recent_data(repo)
    new_recent = data.recent if isinstance(recent, _Keep) else recent
    new_closed = data.closed if isinstance(closed, _Keep) else closed

    obj: dict[str, str | list[str]] = {}
    if new_recent:
        obj["recent"] = new_recent
    if new_closed:
        obj["closed"] = new_closed
    write_text(repo.root / RECENT_FILE, json.dumps(obj) + "\n")


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
    _update_recent_data(repo, recent=task_id)


def save_closed_refs(repo: TaskRepo, closed_ids: list[str]) -> None:
    _update_recent_data(repo, closed=closed_ids)


def load_closed_tasks(repo: TaskRepo) -> list[Task]:
    data = _load_recent_data(repo)
    tasks: list[Task] = []
    for task_id in data.closed:
        try:
            tasks.append(repo.resolve_ref(task_id))
        except TaskValidateError:
            pass
    return tasks


def load_recent_task(repo: TaskRepo) -> Task | None:
    data = _load_recent_data(repo)
    if not data.recent:
        return None

    try:
        return repo.resolve_ref(data.recent)
    except TaskValidateError:
        return None


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
    data = _load_recent_data(repo)
    if not data.recent:
        raise TaskValidateError("Recent task was not set yet", task_ref=task_ref)

    return data.recent
