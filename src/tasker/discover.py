"""Locate or initialize the tasker directory."""

from pathlib import Path
from typing import Iterator

from .exceptions import TaskerError

_TASKER_DIR = "tasker"
_ARCHIVE_DIR = "archive"
_GITKEEP_FILE = ".gitkeep"
_GITIGNORE_FILE = ".gitignore"
_RECENT_FILE = ".recent"


class TaskerNotFoundError(TaskerError):
    def __init__(self) -> None:
        super().__init__(
            "Tasker directory not found."
            " Run 'tasker init' to initialize in the current directory.",
            json_output={"error_type": "tasker_not_found"},
        )


def discover_tasker_dir(start: Path | None = None) -> Path:
    if start is None:
        start = Path.cwd()

    start = start.resolve()

    # 1. search for existing tasker/ folder
    for parent in _walk_parents(start):
        candidate = parent / _TASKER_DIR
        if candidate.is_dir():
            return candidate

    # 2. search for .git/ and auto-init there
    for parent in _walk_parents(start):
        if (parent / ".git").exists():
            return init_tasker_dir(parent)

    # 3. not found
    raise TaskerNotFoundError


def init_tasker_dir(project_root: Path | None = None) -> Path:
    if project_root is None:
        project_root = Path.cwd()

    tasker_dir = project_root / _TASKER_DIR
    tasker_dir.mkdir(exist_ok=True)

    gitignore = tasker_dir / _GITIGNORE_FILE
    if not gitignore.exists():
        gitignore.write_text(_RECENT_FILE + "\n", encoding="utf-8")

    archive_dir = tasker_dir / _ARCHIVE_DIR
    archive_dir.mkdir(exist_ok=True)

    gitkeep = archive_dir / _GITKEEP_FILE
    if not gitkeep.exists():
        gitkeep.write_text("", encoding="utf-8")

    return tasker_dir


def _walk_parents(start: Path) -> Iterator[Path]:
    yield start
    for parent in start.parents:
        yield parent
