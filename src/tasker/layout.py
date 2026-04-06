from pathlib import Path
from typing import Iterator

from tasker.utils import read_text, write_text

from .exceptions import TaskerError

TASKER_DIR = "tasker"
ARCHIVE_DIR = "archive"
_GITKEEP_FILE = ".gitkeep"
_GITIGNORE_FILE = ".gitignore"
_RECENT_FILE = ".recent"
_GITIGNORE_HEADER = "# tasker"


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
        candidate = parent / TASKER_DIR
        if candidate.is_dir() and is_tasker_dir(candidate):
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

    tasker_dir = project_root / TASKER_DIR
    tasker_dir.mkdir(exist_ok=True)

    gitignore = tasker_dir / _GITIGNORE_FILE
    if not gitignore.exists():
        write_text(gitignore, _GITIGNORE_HEADER + "\n" + _RECENT_FILE + "\n")

    archive_dir = tasker_dir / ARCHIVE_DIR
    archive_dir.mkdir(exist_ok=True)

    gitkeep = archive_dir / _GITKEEP_FILE
    if not gitkeep.exists():
        write_text(gitkeep, "")

    return tasker_dir


def is_tasker_dir(candidate: Path) -> bool:
    if (candidate / _RECENT_FILE).exists():
        return True

    gitignore = candidate / _GITIGNORE_FILE
    if gitignore.is_file():
        try:
            text = read_text(gitignore)
        except OSError:
            return False

        if _GITIGNORE_HEADER in text:
            return True

    return False


def _walk_parents(start: Path) -> Iterator[Path]:
    yield start
    for parent in start.parents:
        yield parent
