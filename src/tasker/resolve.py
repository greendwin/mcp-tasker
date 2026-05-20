import re
from typing import NamedTuple

from .base_types import Task
from .exceptions import TaskValidateError
from .layout import CLOSED_FILE, RECENT_FILE, ensure_gitignore_entry
from .parse import find_common_ancestor, make_child_ref, parse_task_ref
from .repo import TaskRepo
from .todo import assign_todo_letters, load_todo_tasks
from .utils import write_text

CLOSED_HISTORY_CAP = 30


class ResolvedRef(NamedTuple):
    task_ref: str  # original task ref, could be recent link aka `qNN`
    task: Task  # resolved task


def resolve_ref(
    repo: TaskRepo,
    task_ref: str,
) -> ResolvedRef:
    if _is_direct_ref(task_ref):
        resolved_ref = _normalize_direct_ref(task_ref)
    else:
        resolved_ref = _resolve_shortcut(repo, task_ref)

    resolved_task = repo.resolve_ref(resolved_ref)

    return ResolvedRef(task_ref, resolved_task)


def _normalize_direct_ref(task_ref: str) -> str:
    m = re.fullmatch(r"s(\d+)(?:t(\d+))?(?:-.*)?", task_ref)
    if not m:
        return task_ref

    s_digits = _normalize_shortcut_digits(task_ref, m.group(1))
    assert s_digits is not None
    result = "s" + s_digits
    if m.group(2) is not None:
        t_digits = _normalize_shortcut_digits(task_ref, m.group(2))
        assert t_digits is not None
        result += "t" + t_digits

    return result


def _is_direct_ref(task_ref: str) -> bool:
    return task_ref.startswith("s")


def _load_recent_id(repo: TaskRepo) -> str | None:
    path = repo.root / RECENT_FILE
    if not path.exists():
        return None

    text = path.read_text().strip()
    if not text or text.startswith("{"):
        # empty or legacy JSON — ignore
        return None

    return text


def _write_recent_id(repo: TaskRepo, task_id: str) -> None:
    write_text(repo.root / RECENT_FILE, task_id + "\n")


def _load_closed_ids(repo: TaskRepo) -> list[str]:
    path = repo.root / CLOSED_FILE
    if not path.exists():
        return []

    return [line.strip() for line in path.read_text().splitlines() if line.strip()]


def _write_closed_ids(repo: TaskRepo, ids: list[str]) -> None:
    path = repo.root / CLOSED_FILE
    new_file = not path.exists()
    write_text(path, "".join(line + "\n" for line in ids))
    if new_file:
        ensure_gitignore_entry(repo.root, CLOSED_FILE)


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
    _write_recent_id(repo, task_id)


def save_closed_refs(repo: TaskRepo, closed_ids: list[str]) -> None:
    if not closed_ids:
        return

    existing = _load_closed_ids(repo)

    # dedup: move re-closed IDs to the newest end
    new_set = set(closed_ids)
    merged = [p for p in existing if p not in new_set]
    merged.extend(closed_ids)

    # cap at the rolling history limit (keep newest)
    if len(merged) > CLOSED_HISTORY_CAP:
        merged = merged[-CLOSED_HISTORY_CAP:]

    _write_closed_ids(repo, merged)


def load_closed_tasks(repo: TaskRepo, *, limit: int) -> list[Task]:
    stored = _load_closed_ids(repo)
    tasks: list[Task] = []
    stale: set[str] = set()

    # iterate newest → oldest
    for task_id in reversed(stored):
        if len(tasks) >= limit:
            break

        try:
            tasks.append(repo.resolve_ref(task_id))
        except TaskValidateError:
            stale.add(task_id)

    if stale:
        pruned = [p for p in stored if p not in stale]
        _write_closed_ids(repo, pruned)

    return tasks


def load_recent_task(repo: TaskRepo) -> Task | None:
    recent_id = _load_recent_id(repo)
    if not recent_id:
        return None

    try:
        return repo.resolve_ref(recent_id)
    except TaskValidateError:
        return None


def _normalize_shortcut_digits(task_ref: str, digits: str | None) -> str | None:
    if digits is None:
        return None
    if len(digits) == 1:
        return "0" + digits
    if len(digits) % 2 == 1:
        raise TaskValidateError(
            f"Ambiguous shortcut digits {task_ref!r}", task_ref=task_ref
        )
    return digits


def _resolve_shortcut(repo: TaskRepo, task_ref: str) -> str:
    if m := re.fullmatch(r"t([a-z])(\d+)?", task_ref):
        digits = _normalize_shortcut_digits(task_ref, m.group(2))
        return _resolve_todo_letter(repo, task_ref, m.group(1), digits)

    if not task_ref.startswith(("p", "q")):
        # resolve as-is, try to resolve in repo
        return task_ref

    recent_id = _load_recent_id(repo)
    if not recent_id:
        raise TaskValidateError("Recent task was not set yet", task_ref=task_ref)

    if task_ref == "q":
        return recent_id

    # links like q0102
    if m := re.fullmatch(r"q(\d+)", task_ref):
        digits = _normalize_shortcut_digits(task_ref, m.group(1))
        assert digits is not None
        return make_child_ref(recent_id, digits)

    # links like p, p01, pp, pp0102
    if m := re.fullmatch(r"(p+)(\d+)?", task_ref):
        ancestor_id = recent_id
        for _ in range(len(m.group(1))):
            ancestor_id = parse_task_ref(ancestor_id).parent_id
        digits = _normalize_shortcut_digits(task_ref, m.group(2))

        if digits:
            return make_child_ref(ancestor_id, digits)
        return ancestor_id

    raise TaskValidateError(f"Invalid recent reference {task_ref!r}", task_ref=task_ref)


def _resolve_todo_letter(
    repo: TaskRepo, task_ref: str, letter: str, digits: str | None
) -> str:
    todo_tasks = load_todo_tasks(repo)
    letters = assign_todo_letters(todo_tasks)
    target = f"t{letter}"
    for task_id, assigned in letters.items():
        if assigned == target:
            if digits:
                return make_child_ref(task_id, digits)
            return task_id

    raise TaskValidateError(f"Unknown todo shortcut {task_ref!r}", task_ref=task_ref)
