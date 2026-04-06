from pathlib import Path

import pytest

from tasker.cli import app
from tasker.layout import (
    ARCHIVE_DIR,
    TASKER_DIR,
    TaskerNotFoundError,
    discover_tasker_dir,
    init_tasker_dir,
    is_tasker_dir,
)

from .helpers import assert_invoke


def _make_tasker_dir(parent: Path) -> Path:
    """Create a tasker dir with the gitignore header so it's recognized."""
    d = parent / TASKER_DIR
    d.mkdir(exist_ok=True)
    (d / ".gitignore").write_text("# tasker\n.recent\n")
    return d


def test_discover_finds_tasker_in_current_dir(project_root: Path) -> None:
    tasker_dir = _make_tasker_dir(project_root)

    result = discover_tasker_dir(project_root)
    assert result == tasker_dir


def test_discover_finds_tasker_in_parent_dir(project_root: Path) -> None:
    tasker_dir = _make_tasker_dir(project_root)

    child = project_root / "subdir"
    child.mkdir()

    result = discover_tasker_dir(child)
    assert result == tasker_dir


def test_discover_auto_inits_near_git(project_root: Path) -> None:
    result = discover_tasker_dir(project_root)

    assert result == project_root / TASKER_DIR
    assert result.is_dir()
    assert (result / ".gitignore").exists()
    content = (result / ".gitignore").read_text()
    assert "# tasker" in content
    assert ".recent" in content


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
    _make_tasker_dir(inner)

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


def test_init_creates_gitignore_with_header_and_recent(
    project_root: Path,
) -> None:
    init_tasker_dir(project_root)

    gitignore = project_root / TASKER_DIR / ".gitignore"
    assert gitignore.exists()
    content = gitignore.read_text()
    assert content.startswith("# tasker\n")
    assert ".recent" in content


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


def test_discover_skips_accidental_tasker_dir(project_root: Path) -> None:
    """A bare 'tasker/' dir without markers must not be recognized."""
    bare = project_root / TASKER_DIR
    bare.mkdir()

    result = discover_tasker_dir(project_root)
    # bare dir is skipped; auto-init creates a proper one
    assert result == bare
    assert is_tasker_dir(result)


def test_discover_skips_foreign_tasker_above_git(project_root: Path) -> None:
    """A sibling 'tasker/' dir outside the current repo must not be found."""
    sibling_tasker = Path("/") / TASKER_DIR
    sibling_tasker.mkdir()

    subdir = project_root / "src"
    subdir.mkdir()

    result = discover_tasker_dir(subdir)
    assert result == project_root / TASKER_DIR
    assert result != sibling_tasker


def test_discover_finds_tasker_above_git(project_root: Path) -> None:
    """An inited tasker/ dir above .git should be found."""
    parent = project_root.parent
    _make_tasker_dir(parent)

    result = discover_tasker_dir(project_root)
    assert result == parent / TASKER_DIR


def test_is_tasker_dir_with_recent_file(project_root: Path) -> None:
    d = project_root / TASKER_DIR
    d.mkdir()
    (d / ".recent").write_text("s01t01\n")

    assert is_tasker_dir(d)


def test_is_tasker_dir_with_gitignore_header(project_root: Path) -> None:
    d = project_root / TASKER_DIR
    d.mkdir()
    (d / ".gitignore").write_text("# tasker\n.recent\n")

    assert is_tasker_dir(d)


def test_is_tasker_dir_bare_dir(project_root: Path) -> None:
    d = project_root / TASKER_DIR
    d.mkdir()

    assert not is_tasker_dir(d)


def test_discover_error_message_suggests_init() -> None:
    nowhere = Path("/empty")
    nowhere.mkdir()

    with pytest.raises(TaskerNotFoundError, match="tasker init"):
        discover_tasker_dir(nowhere)
