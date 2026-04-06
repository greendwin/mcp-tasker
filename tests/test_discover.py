from pathlib import Path

import pytest

from tasker.cli import app
from tasker.layout import (
    ARCHIVE_DIR,
    TASKER_DIR,
    TaskerNotFoundError,
    discover_tasker_dir,
    get_user_tasker_dir,
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


def test_discover_does_not_auto_init_near_git() -> None:
    bare = Path("/bare-project")
    bare.mkdir()
    (bare / ".git").mkdir()

    with pytest.raises(TaskerNotFoundError):
        discover_tasker_dir(bare)


def test_discover_does_not_auto_init_from_subdir() -> None:
    bare = Path("/bare-project")
    bare.mkdir()
    (bare / ".git").mkdir()

    child = bare / "src" / "pkg"
    child.mkdir(parents=True)

    with pytest.raises(TaskerNotFoundError):
        discover_tasker_dir(child)


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


def test_init_preserves_existing_gitignore() -> None:
    root = Path("/preserve-gitignore")
    root.mkdir()
    tasker_dir = root / TASKER_DIR
    tasker_dir.mkdir()
    gitignore = tasker_dir / ".gitignore"
    gitignore.write_text("custom\n.recent\n")

    init_tasker_dir(root)

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


def test_discover_skips_accidental_tasker_dir() -> None:
    """A bare 'tasker/' dir without markers must not be recognized."""
    bare_proj = Path("/bare-proj2")
    bare_proj.mkdir()
    (bare_proj / TASKER_DIR).mkdir()

    with pytest.raises(TaskerNotFoundError):
        discover_tasker_dir(bare_proj)


def test_discover_skips_foreign_tasker_above_git() -> None:
    """A bare 'tasker/' dir outside the current repo must not be found."""
    bare_proj = Path("/bare-proj3")
    bare_proj.mkdir()
    (bare_proj / ".git").mkdir()

    sibling_tasker = Path("/") / TASKER_DIR
    sibling_tasker.mkdir(exist_ok=True)

    subdir = bare_proj / "src"
    subdir.mkdir()

    with pytest.raises(TaskerNotFoundError):
        discover_tasker_dir(subdir)


def test_discover_finds_tasker_above_git() -> None:
    """An inited tasker/ dir above .git should be found."""
    parent = Path("/outer-proj")
    parent.mkdir()
    _make_tasker_dir(parent)

    child = parent / "inner"
    child.mkdir()
    (child / ".git").mkdir()

    result = discover_tasker_dir(child)
    assert result == parent / TASKER_DIR


def test_is_tasker_dir_with_recent_file() -> None:
    d = Path("/test-is-dir/tasker")
    d.mkdir(parents=True)
    (d / ".recent").write_text("s01t01\n")

    assert is_tasker_dir(d)


def test_is_tasker_dir_with_gitignore_header() -> None:
    d = Path("/test-is-dir2/tasker")
    d.mkdir(parents=True)
    (d / ".gitignore").write_text("# tasker\n.recent\n")

    assert is_tasker_dir(d)


def test_is_tasker_dir_bare_dir() -> None:
    d = Path("/test-is-dir3/tasker")
    d.mkdir(parents=True)

    assert not is_tasker_dir(d)


def test_discover_error_message_suggests_init() -> None:
    nowhere = Path("/empty")
    nowhere.mkdir()

    with pytest.raises(TaskerNotFoundError, match="tasker init"):
        discover_tasker_dir(nowhere)


# --- user-level tasker ---


def test_get_user_tasker_dir_xdg_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    result = get_user_tasker_dir()
    assert result == Path.home() / ".local" / "share" / TASKER_DIR


def test_get_user_tasker_dir_xdg_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", "/custom/data")
    result = get_user_tasker_dir()
    assert result == Path("/custom/data") / TASKER_DIR


def test_get_user_tasker_dir_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    import platform

    monkeypatch.setattr(platform, "system", lambda: "Windows")
    monkeypatch.setenv("LOCALAPPDATA", "C:\\Users\\me\\AppData\\Local")
    result = get_user_tasker_dir()
    assert result == Path("C:\\Users\\me\\AppData\\Local") / TASKER_DIR


def test_discover_finds_user_level_tasker() -> None:
    user_dir = get_user_tasker_dir()
    user_dir.mkdir(parents=True)
    (user_dir / ".gitignore").write_text("# tasker\n.recent\n")

    # no project-level tasker, should fall back to user-level
    bare = Path("/no-tasker-proj")
    bare.mkdir()
    result = discover_tasker_dir(bare)
    assert result == user_dir


def test_discover_prefers_project_over_user(project_root: Path) -> None:
    # set up user-level
    user_dir = get_user_tasker_dir()
    user_dir.mkdir(parents=True)
    (user_dir / ".gitignore").write_text("# tasker\n.recent\n")

    # set up project-level
    proj_tasker = _make_tasker_dir(project_root)

    result = discover_tasker_dir(project_root)
    assert result == proj_tasker


def test_init_user_cli_command(project_root: Path) -> None:
    (project_root / ".git").rmdir()

    result = assert_invoke(app, ["init", "--user"])
    assert "Initialized tasker" in result.output

    user_dir = get_user_tasker_dir()
    assert user_dir.is_dir()
    assert (user_dir / ".gitignore").exists()
    assert (user_dir / ARCHIVE_DIR).is_dir()
