import traceback
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.markup import escape as _rich_escape

from .exceptions import TaskerError


def escape_markup(text: str) -> str:
    # escape `[tag]`-like sequences so rich prints them literally
    return _rich_escape(text)


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

    @contextmanager
    def catching_errors(self) -> Iterator[None]:
        self._json_output_obj = {}
        try:
            yield
        except click.ClickException:
            raise
        except TaskerError as ex:
            self._handle_error(ex, file_path=ex.file_path, json_output=ex.json_output)
        except Exception as ex:
            self._handle_error(ex)
        finally:
            if self.json_output:
                self._console.print_json(data=self._json_output_obj)

    def _handle_error(
        self,
        ex: Exception,
        *,
        file_path: Path | None = None,
        json_output: dict[str, Any] | None = None,
    ) -> None:
        if not self.json_output:
            if self.debug:
                raise

            if file_path:
                self.print(f"[dim]File: {escape_markup(str(file_path))}[/dim]")

            self.print(f"[red]Error:[/red] {escape_markup(str(ex))}")
            raise SystemExit(1) from ex

        self._json_output_obj = {"error": str(ex)}
        if json_output:
            self._json_output_obj.update(json_output)
        if self.debug:
            self._json_output_obj["traceback"] = traceback.format_exc()
        raise SystemExit(1) from ex


console = OutputContext()


def read_text(path: Path) -> str:
    try:
        return path.read_text("utf-8")
    except OSError as ex:
        raise TaskerError(str(ex), file_path=path) from ex


def write_text(path: Path, content: str) -> None:
    try:
        path.parent.mkdir(exist_ok=True, parents=True)
        path.write_text(content, encoding="utf-8")
    except OSError as ex:
        raise TaskerError(str(ex), file_path=path) from ex
