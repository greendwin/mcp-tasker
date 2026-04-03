from typing import Annotated

import typer
from typer_di import TyperDI

from tasker import __version__
from tasker.discover import discover_tasker_dir, init_tasker_dir
from tasker.repo import TaskRepo
from tasker.utils import console

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
    tasker_dir = discover_tasker_dir()
    return TaskRepo(tasker_dir)


@app.command("init", help="Initialize tasker in the current directory.")
@console.catching_output
def cmd_init() -> None:
    tasker_dir = init_tasker_dir()
    console.print(
        f"[green]Initialized tasker in [blue]{tasker_dir}[/blue][/green]",
        json_output={"tasker_dir": str(tasker_dir)},
    )
