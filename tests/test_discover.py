from pathlib import Path

import pytest

from tasker.cli import app
from tasker.layout import (
    ARCHIVE_DIR,
    TASKER_DIR,
    TaskerNotFoundError,
    discover_tasker_dir,
    init_tasker_dir,
)

from .helpers import assert_invoke


def test_discover_finds_tasker_in_current_dir(project_root: Path) -> None:
    tasker_dir = project_root / TASKER_DIR
    tasker_dir.mkdir()

    result = discover_tasker_dir(project_root)
    assert result == tasker_dir


def test_discover_finds_tasker_in_parent_dir(project_root: Path) -> None:
    tasker_dir = project_root / TASKER_DIR
    tasker_dir.mkdir()

    child = project_root / "subdir"
    child.mkdir()

    result = discover_tasker_dir(child)
    assert result == tasker_dir


def test_discover_auto_inits_near_git(project_root: Path) -> None:
    result = discover_tasker_dir(project_root)

    assert result == project_root / TASKER_DIR
    assert result.is_dir()
    assert (result / ".gitignore").exists()
    assert ".recent" in (result / ".gitignore").read_text()


def test_discover_auto_inits_from_subdir(project_root: Path) -> None:
    child = project_root / "src" / "pkg"
    child.mkdir(parents=True)

    result = discover_tasker_dir(child)

    assert result == project_root / TASKER_DIR
    assert result.is_dir()


def test_discover_prefers_existing_tasker_over_git() -> None:
    """If tasker/ exists in a subdirectory closer than .git, use it."""
    root = Path("/outer")
    root.mkdir()
    (root / ".git").mkdir()

    inner = root / "inner"
    inner.mkdir()
    (inner / TASKER_DIR).mkdir()

    result = discover_tasker_dir(inner)
    assert result == inner / TASKER_DIR


def test_discover_raises_without_git_or_tasker() -> None:
    nowhere = Path("/no-project")
    nowhere.mkdir()

    with pytest.raises(TaskerNotFoundError):
        discover_tasker_dir(nowhere)


def test_init_creates_tasker_dir(project_root: Path) -> None:
    result = init_tasker_dir(project_root)

    assert result == project_root / TASKER_DIR
    assert result.is_dir()


def test_init_creates_gitignore_with_recent(project_root: Path) -> None:
    init_tasker_dir(project_root)

    gitignore = project_root / TASKER_DIR / ".gitignore"
    assert gitignore.exists()
    assert ".recent" in gitignore.read_text()


def test_init_creates_archive_with_gitkeep(project_root: Path) -> None:
    init_tasker_dir(project_root)

    archive_dir = project_root / TASKER_DIR / ARCHIVE_DIR
    assert archive_dir.is_dir()
    assert (archive_dir / ".gitkeep").exists()


def test_init_idempotent(project_root: Path) -> None:
    init_tasker_dir(project_root)
    init_tasker_dir(project_root)

    gitignore = project_root / TASKER_DIR / ".gitignore"
    assert gitignore.read_text().count(".recent") == 1
    assert (project_root / TASKER_DIR / ARCHIVE_DIR / ".gitkeep").exists()


def test_init_preserves_existing_gitignore(project_root: Path) -> None:
    tasker_dir = project_root / TASKER_DIR
    tasker_dir.mkdir()
    gitignore = tasker_dir / ".gitignore"
    gitignore.write_text("custom\n.recent\n")

    init_tasker_dir(project_root)

    assert gitignore.read_text() == "custom\n.recent\n"


def test_init_cli_command(project_root: Path) -> None:
    # remove .git so discovery doesn't auto-init
    (project_root / ".git").rmdir()

    result = assert_invoke(app, ["init"])
    assert "Initialized tasker" in result.output
    assert (project_root / TASKER_DIR).is_dir()


def test_init_cli_json_output(project_root: Path) -> None:
    (project_root / ".git").rmdir()

    result = assert_invoke(app, ["--json-output", "init"])
    assert "tasker_dir" in result.output


def test_discover_error_message_suggests_init() -> None:
    nowhere = Path("/empty")
    nowhere.mkdir()

    with pytest.raises(TaskerNotFoundError, match="tasker init"):
        discover_tasker_dir(nowhere)
