import string
from typing import NamedTuple

from .base_types import Task
from .exceptions import TaskValidateError
from .layout import TODO_FILE, ensure_gitignore_entry
from .repo import TaskRepo
from .utils import read_text, write_text


def load_todo_ids(repo: TaskRepo) -> list[str]:
    path = repo.root / TODO_FILE
    if not path.exists():
        return []

    text = read_text(path).strip()
    if not text:
        return []

    return [line.strip() for line in text.splitlines() if line.strip()]


def save_todo_ids(repo: TaskRepo, todo_ids: list[str]) -> None:
    path = repo.root / TODO_FILE
    if not todo_ids:
        if path.exists():
            path.unlink()
        return

    if not path.exists():
        ensure_gitignore_entry(repo.root, TODO_FILE)

    write_text(path, "\n".join(todo_ids) + "\n")


def add_todo(repo: TaskRepo, task_id: str) -> bool:
    todo_ids = load_todo_ids(repo)
    if task_id in todo_ids:
        return False

    todo_ids.append(task_id)
    save_todo_ids(repo, todo_ids)
    return True


class TodoClassification(NamedTuple):
    active: list[Task]
    all_finished: bool


def classify_todo(tasks: list[Task]) -> TodoClassification:
    # `all_finished is True` only when the list is non-empty but every task is
    # closed -- distinct from an empty list (no tasks at all).
    active = [t for t in tasks if not t.is_closed]
    return TodoClassification(active=active, all_finished=bool(tasks) and not active)


def load_todo_tasks(repo: TaskRepo) -> list[Task]:
    todo_ids = load_todo_ids(repo)
    if not todo_ids:
        return []

    live: list[Task] = []
    live_ids: list[str] = []
    for task_id in todo_ids:
        try:
            task = repo.resolve_ref(task_id)
        except TaskValidateError:
            continue

        live.append(task)
        live_ids.append(task.id)

    if live_ids != todo_ids:
        save_todo_ids(repo, live_ids)

    return live


def assign_todo_letters(tasks: list[Task]) -> dict[str, str]:
    result: dict[str, str] = {}
    i = 0
    for task in tasks:
        if task.is_closed:
            continue
        if i >= len(string.ascii_lowercase):
            break
        result[task.id] = f"t{string.ascii_lowercase[i]}"
        i += 1
    return result


def remove_todo(repo: TaskRepo, task_id: str) -> bool:
    todo_ids = load_todo_ids(repo)
    if task_id not in todo_ids:
        return False

    todo_ids.remove(task_id)
    save_todo_ids(repo, todo_ids)
    return True
