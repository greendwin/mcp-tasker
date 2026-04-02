import os
import platform
import re
import subprocess
from pathlib import Path
from typing import Annotated

import typer
from typer_di import TyperDI

from tasker import __version__
from tasker.base_types import Task
from tasker.exceptions import TaskArchivedError, TaskValidateError
from tasker.parse import make_child_ref, parse_task_ref
from tasker.repo import TaskRepo
from tasker.utils import JsonAppend, console, read_text, write_text

_RECENT_FILE = ".recent"
_GITIGNORE_FILE = ".gitignore"


app = TyperDI(
    name="tasker",
    help="File-based task tracker for git repos.",
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"tasker {__version__}")
        raise typer.Exit()


@app.callback()
def common_options(
    version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            "-V",
            is_eager=True,
            callback=_version_callback,
            help="Show version and exit.",
        ),
    ] = None,
    debug: Annotated[
        bool, typer.Option("--debug", help="Show full tracebacks on errors.")
    ] = False,
    json_output: Annotated[
        bool, typer.Option("--json-output", help="Output result in json format.")
    ] = False,
) -> None:
    console.debug = debug
    console.json_output = json_output


def get_task_repo() -> TaskRepo:
    tasker_dir = Path("tasker")
    tasker_dir.mkdir(exist_ok=True)
    return TaskRepo(tasker_dir)


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
            f"[yellow]Unarchiving [blue]{root.ref}[/blue] automatically.[/yellow]",
            json_output={"unarchived_ref": JsonAppend(ref.root_id)},
        )

    try:
        task = repo.resolve_ref(task_ref)
    except TaskArchivedError as ex:
        if console.json_output:
            raise

        console.print(f"[yellow]Task [blue]{ex.task_ref}[/blue] is archived.[/yellow]")
        console.print("Unarchive it first before performing actions on it.")
        raise typer.Exit(1) from ex

    if save_recent and is_direct_link:
        save_recent_task(repo, task.id)

    return task


def save_recent_task(repo: TaskRepo, task_id: str) -> None:
    _ensure_gitignore(repo.root)
    write_text(repo.root / _RECENT_FILE, task_id + "\n")


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


def _ensure_gitignore(root: Path) -> None:
    gitignore = root / _GITIGNORE_FILE
    if not gitignore.exists():
        write_text(gitignore, _GITIGNORE_FILE + "\n" + _RECENT_FILE + "\n")
        return

    content = read_text(gitignore)
    if _RECENT_FILE in content.splitlines():
        return
    if not content.endswith("\n"):
        content += "\n"
    content += _RECENT_FILE + "\n"
    write_text(gitignore, content)


def edit_task_in_editor(repo: TaskRepo, task: Task) -> None:
    # make sure that task is not inline
    if task.is_inline:
        repo.upgrade_to_filebased(task)
        repo.flush_to_disk()

    task_path = repo.build_task_path(task)
    run_editor(task_path.resolve())

    # after edit many things can be changed including `slug`
    # if so - reload full tree and flush it back
    reload = TaskRepo(repo.root)
    _ = reload.resolve_ref(task.ref)
    reload.flush_to_disk()


def run_editor(path: Path) -> None:
    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR")
    if not editor:
        editor = "notepad" if platform.system() == "Windows" else "vi"

    subprocess.run([editor, str(path)])
