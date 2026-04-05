import os
import platform
import subprocess
from pathlib import Path

from tasker.base_types import Task
from tasker.repo._task_repo import TaskRepo


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
