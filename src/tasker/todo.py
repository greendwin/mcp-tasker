import string
from typing import NamedTuple

from .base_types import Task
from .exceptions import TaskNotFoundError
from .layout import TODO_FILE, ensure_gitignore_entry
from .repo import TaskRepo
from .utils import read_text, write_text


def load_todo_list(repo: TaskRepo) -> list[str]:
    path = repo.root / TODO_FILE
    if not path.exists():
        return []

    text = read_text(path).strip()
    if not text:
        return []

    r = []
    for line in text.splitlines():
        if task_id := line.strip():
            r.append(task_id)
    return r


def resolve_todo_tasks(repo: TaskRepo, todo: list[str]) -> list[Task]:
    r = []
    has_invalid = False
    for task_id in todo:
        try:
            task = repo.resolve_ref(task_id)
        except TaskNotFoundError:
            # ignore outdated references
            has_invalid = True
        else:
            r.append(task)

    if has_invalid:
        # update original list, drop invalid tasks
        save_todo_list(repo, [p.id for p in r])
    return r


def save_todo_list(repo: TaskRepo, todo: list[str]) -> None:
    path = repo.root / TODO_FILE
    if not todo:
        if path.exists():
            path.unlink()
        return

    if not path.exists():
        ensure_gitignore_entry(repo.root, TODO_FILE)

    write_text(path, "\n".join(todo) + "\n")


class TodoClassification(NamedTuple):
    active: list[Task]
    all_finished: bool


def classify_todo(tasks: list[Task]) -> TodoClassification:
    # `all_finished is True` only when the list is non-empty but every task is
    # closed -- distinct from an empty list (no tasks at all).
    active = [t for t in tasks if not t.is_closed]
    return TodoClassification(active=active, all_finished=bool(tasks) and not active)


def assign_todo_letters(todo: list[Task]) -> dict[str, str]:
    result: dict[str, str] = {}
    i = 0
    for task in todo:
        if task.is_closed:
            continue

        if i >= len(string.ascii_lowercase):
            break

        result[task.id] = f"t{string.ascii_lowercase[i]}"
        i += 1

    return result
