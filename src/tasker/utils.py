import functools
import traceback
from collections.abc import Callable
from pathlib import Path
from typing import Any, ParamSpec

import typer
from rich.console import Console

from .exceptions import TaskerError

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
        self, text: str, *, end: str = "\n", json_output: dict[str, Any] | None = None
    ) -> None:
        if json_output:
            for k, v in json_output.items():
                if isinstance(v, JsonAppend):
                    self.append_json_output(k, v.value)
                    continue

                assert (
                    k not in self._json_output_obj
                ), f"json_output key {k!r} already set"
                self._json_output_obj[k] = v

        if not self.json_output:
            self._console.print(text, end=end)

    def append_json_output(self, key: str, value: Any) -> None:
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
                    console.print(f"[red]Error:[/red] {ex}")
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
