import os
import platform
import subprocess
from pathlib import Path

from tasker.base_types import Task
from tasker.repo._task_repo import TaskRepo


def edit_task_in_editor(repo: TaskRepo, task: Task) -> None:
    # make sure that task is not inline
    if task.is_inline:
        repo.upgrade_to_filebased(task)

    # flush to ensure filename matches current slug
    # (slug may have been changed externally or via --slug)
    repo.flush_to_disk()

    task_path = repo.build_task_path(task)
    run_editor(task_path.resolve())

    # editor may have changed title/slug/description/inline subtasks;
    # refresh the in-memory tree in place so held Task references stay valid
    repo.reload_root_tree(task)
    repo.flush_to_disk()


def run_editor(path: Path) -> None:
    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR")
    if not editor:
        editor = "notepad" if platform.system() == "Windows" else "vi"

    subprocess.run([editor, str(path)])
