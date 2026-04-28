from collections.abc import Iterator
from typing import Annotated

import click
import typer
from typer.core import TyperGroup
from typer_di import TyperDI

from tasker import __version__
from tasker.base_types import Task, TaskStatus, walk_tasks
from tasker.layout import discover_tasker_dir, get_user_tasker_dir, init_tasker_dir
from tasker.parse import detect_task_type, parse_task_file, parse_task_ref
from tasker.repo import TaskRepo
from tasker.utils import JsonAppend, console


class _TaskerGroup(TyperGroup):
    def invoke(self, ctx: click.Context) -> None:
        with console.catching_errors():
            super().invoke(ctx)


app = TyperDI(
    name="tasker",
    cls=_TaskerGroup,
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


def complete_task_ref(
    ctx: click.Context, args: list[str], incomplete: str
) -> list[tuple[str, str]]:
    try:
        tasker_dir = discover_tasker_dir()
    except Exception:
        return []

    items: list[tuple[str, str]] = []
    repo = TaskRepo(tasker_dir)
    for task_path in repo.list_root_tasks():
        try:
            result = parse_task_file(task_path)
        except Exception:
            continue

        if result.task.ref.startswith(incomplete):
            items.append((result.task.ref, result.task.title))

        for subtask in result.subtasks:
            if subtask.ref.startswith(incomplete):
                items.append((subtask.ref, subtask.title))

    return items


def get_task_repo() -> TaskRepo:
    tasker_dir = discover_tasker_dir()
    return TaskRepo(tasker_dir)


@app.command("init", help="Initialize tasker in the current directory or user home.")
def cmd_init(
    user: Annotated[
        bool,
        typer.Option("--user", help="Initialize user-level tasker."),
    ] = False,
) -> None:
    if user:
        tasker_dir = init_tasker_dir(get_user_tasker_dir().parent)
    else:
        tasker_dir = init_tasker_dir()

    console.print(
        f"[green]Initialized tasker in [blue]{tasker_dir}[/blue][/green]",
        context={"tasker_dir": str(tasker_dir)},
    )


def iter_in_review_tasks(repo: TaskRepo) -> Iterator[Task]:
    for task_path in repo.list_root_tasks(archived=False):
        tp = detect_task_type(task_path)
        if tp is None:
            continue

        root = repo.resolve_ref(tp.task_ref)
        for t in walk_tasks(root):
            if t.status == TaskStatus.IN_REVIEW:
                yield t


def unarchive_task(repo: TaskRepo, task: Task) -> bool:
    if not task.archived:
        return False

    ref = parse_task_ref(task.id)
    root_task = repo.resolve_ref(ref.root_id)

    for t in walk_tasks(root_task):
        t.archived = False
    repo.flush_to_disk()

    console.print(
        f"[yellow]Unarchiving [blue]{root_task.ref}[/blue] automatically[/yellow]",
        context={"unarchived_ref": JsonAppend(ref.root_id)},
    )
    return True
