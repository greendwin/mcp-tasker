import os
import platform
from pathlib import Path
from typing import Iterator

from tasker.utils import read_text, write_text

from .exceptions import TaskerError

TASKER_DIR = "tasker"
ARCHIVE_DIR = "archive"
GITKEEP_FILE = ".gitkeep"
GITIGNORE_FILE = ".gitignore"
RECENT_FILE = ".recent"
TODO_FILE = ".todo"
_GITIGNORE_HEADER = "# tasker"


class TaskerNotFoundError(TaskerError):
    def __init__(self) -> None:
        super().__init__(
            "Tasker directory not found."
            " Run 'tasker init' or 'tasker init --user' to initialize.",
            json_output={"error_type": "tasker_not_found"},
        )


def get_user_tasker_dir() -> Path:
    if platform.system() == "Windows":
        base = os.environ.get("LOCALAPPDATA")
        if base:
            return Path(base) / TASKER_DIR
        return Path.home() / "AppData" / "Local" / TASKER_DIR
    else:
        base = os.environ.get("XDG_DATA_HOME")
        if base:
            return Path(base) / TASKER_DIR
        return Path.home() / ".local" / "share" / TASKER_DIR


def discover_tasker_dir(start: Path | None = None) -> Path:
    if start is None:
        start = Path.cwd()

    start = start.resolve()

    # 1. search for existing tasker/ folder in project tree
    for parent in _walk_parents(start):
        candidate = parent / TASKER_DIR
        if candidate.is_dir() and is_tasker_dir(candidate):
            return candidate

    # 2. check user-level tasker dir
    user_dir = get_user_tasker_dir()
    if user_dir.is_dir() and is_tasker_dir(user_dir):
        return user_dir

    # 3. not found
    raise TaskerNotFoundError


def init_tasker_dir(project_root: Path | None = None) -> Path:
    if project_root is None:
        project_root = Path.cwd()

    tasker_dir = project_root / TASKER_DIR
    tasker_dir.mkdir(parents=True, exist_ok=True)

    gitignore = tasker_dir / GITIGNORE_FILE
    if not gitignore.exists():
        write_text(
            gitignore,
            _GITIGNORE_HEADER + "\n" + RECENT_FILE + "\n" + TODO_FILE + "\n",
        )

    archive_dir = tasker_dir / ARCHIVE_DIR
    archive_dir.mkdir(exist_ok=True)

    gitkeep = archive_dir / GITKEEP_FILE
    if not gitkeep.exists():
        write_text(gitkeep, "")

    return tasker_dir


def is_tasker_dir(candidate: Path) -> bool:
    if (candidate / RECENT_FILE).exists():
        return True

    gitignore = candidate / GITIGNORE_FILE
    if gitignore.is_file():
        try:
            text = read_text(gitignore)
        except OSError:
            return False

        if _GITIGNORE_HEADER in text:
            return True

    return False


def ensure_gitignore_entry(tasker_dir: Path, entry: str) -> None:
    gitignore_path = tasker_dir / GITIGNORE_FILE
    if not gitignore_path.exists():
        return

    text = read_text(gitignore_path)
    for line in text.splitlines():
        if line.strip() == entry:
            return

    write_text(gitignore_path, text.rstrip("\n") + "\n" + entry + "\n")


def _walk_parents(start: Path) -> Iterator[Path]:
    yield start
    for parent in start.parents:
        yield parent
