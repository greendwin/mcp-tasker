from .layout import TODO_FILE, ensure_gitignore_entry
from .repo import TaskRepo
from .utils import read_text, write_text


def load_todo_ids(repo: TaskRepo) -> set[str]:
    path = repo.root / TODO_FILE
    if not path.exists():
        return set()

    text = read_text(path).strip()
    if not text:
        return set()

    return {line.strip() for line in text.splitlines() if line.strip()}


def save_todo_ids(repo: TaskRepo, todo_ids: set[str]) -> None:
    path = repo.root / TODO_FILE
    if not todo_ids:
        if path.exists():
            path.unlink()
        return

    if not path.exists():
        ensure_gitignore_entry(repo.root, TODO_FILE)

    lines = sorted(todo_ids)
    write_text(path, "\n".join(lines) + "\n")


def add_todo(repo: TaskRepo, task_id: str) -> bool:
    todo_ids = load_todo_ids(repo)
    if task_id in todo_ids:
        return False
    todo_ids.add(task_id)
    save_todo_ids(repo, todo_ids)
    return True


def remove_todo(repo: TaskRepo, task_id: str) -> bool:
    todo_ids = load_todo_ids(repo)
    if task_id not in todo_ids:
        return False
    todo_ids.discard(task_id)
    save_todo_ids(repo, todo_ids)
    return True
