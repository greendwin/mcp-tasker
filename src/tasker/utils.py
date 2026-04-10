import functools
import traceback
from collections.abc import Callable
from pathlib import Path
from typing import Any, ParamSpec

import typer
from rich.console import Console
from rich.markup import escape as _rich_escape

from .exceptions import TaskerError


def escape_markup(text: str) -> str:
    # escape `[tag]`-like sequences so rich prints them literally
    return _rich_escape(text)


_P = ParamSpec("_P")


class JsonAppend:
    """Marker that tells OutputContext to append the value to a list."""

    __slots__ = ("value",)

    def __init__(self, value: Any) -> None:
        self.value = value


class OutputContext:
    debug: bool = False
    json_output: bool = False

    def __init__(self) -> None:
        self._console = Console()
        self._json_output_obj: dict[str, Any] = {}

    def print(
        self, text: str, *, end: str = "\n", context: dict[str, Any] | None = None
    ) -> None:
        if context:
            for k, v in context.items():
                self.set_context(k, v)

        if not self.json_output:
            self._console.print(text, end=end)

    def set_context(self, key: str, value: Any) -> None:
        if isinstance(value, JsonAppend):
            self.append_context(key, value.value)
            return

        if key in self._json_output_obj:
            raise AssertionError(f"json_output key {key!r} already set")

        self._json_output_obj[key] = value

    def append_context(self, key: str, value: Any) -> None:
        arr = self._json_output_obj.setdefault(key, [])
        assert isinstance(arr, list), f"json_output key {key!r} is not a list"
        arr.append(value)

    def catching_output(self, fn: Callable[_P, None]) -> Callable[_P, None]:
        @functools.wraps(fn)
        def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> None:
            self._json_output_obj = {}
            try:
                fn(*args, **kwargs)
            except TaskerError as ex:
                if not self.json_output:
                    if self.debug:
                        raise
                    console.print(f"[red]Error:[/red] {escape_markup(str(ex))}")
                    raise typer.Exit(1) from ex

                self._json_output_obj = {"error": str(ex)}
                self._json_output_obj.update(ex.json_output)
                if self.debug:
                    self._json_output_obj["traceback"] = traceback.format_exc()
                raise typer.Exit(1) from ex
            except Exception as ex:
                if not self.json_output:
                    raise

                self._json_output_obj = {
                    "error": str(ex),
                    "traceback": traceback.format_exc(),
                }
                raise typer.Exit(1) from ex
            finally:
                if self.json_output:
                    self._console.print_json(data=self._json_output_obj)

        return wrapper


console = OutputContext()


def read_text(path: Path) -> str:
    return path.read_text("utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(exist_ok=True, parents=True)
    path.write_text(content, encoding="utf-8")
