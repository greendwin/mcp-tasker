from pathlib import Path
from unittest import mock

from tasker.cli import app

from .helpers import add_subtask, assert_invoke, create_task

# ---------------------------------------------------------------------------
# new --editor
# ---------------------------------------------------------------------------


def test_new_editor_calls_open_in_editor(run_editor: mock.Mock) -> None:
    assert_invoke(app, ["new", "My story", "--editor"])
    assert run_editor.call_count == 1


def test_new_editor_short_flag(run_editor: mock.Mock) -> None:
    assert_invoke(app, ["new", "My story", "-e"])
    assert run_editor.call_count == 1


def test_new_editor_opens_md_file(run_editor: mock.Mock) -> None:
    assert_invoke(app, ["new", "My story", "--editor"])
    opened_path: Path = run_editor.call_args[0][0]
    assert opened_path.suffix == ".md"


def test_new_editor_creates_file_based_task(
    tasks_root: Path, run_editor: mock.Mock
) -> None:
    create_task("My story")
    assert_invoke(app, ["new", "Second story", "--editor"])
    task_files = list(tasks_root.glob("s02-*.md"))
    assert len(task_files) == 1


def test_new_editor_without_details_still_creates_file(
    tasks_root: Path, run_editor: mock.Mock
) -> None:
    # --editor alone (no --details) must still produce a file-based task
    assert_invoke(app, ["new", "Bare story", "--editor"])
    task_files = list(tasks_root.glob("s01-*.md"))
    assert len(task_files) == 1
    opened_path: Path = run_editor.call_args[0][0]
    assert opened_path.exists()


def test_new_editor_combined_with_details(
    tasks_root: Path, run_editor: mock.Mock
) -> None:
    assert_invoke(app, ["new", "Story", "--details", "Some desc", "--editor"])
    task_files = list(tasks_root.glob("s01-*.md"))
    assert len(task_files) == 1
    assert run_editor.call_count == 1


# ---------------------------------------------------------------------------
# add --editor
# ---------------------------------------------------------------------------


def test_add_editor_calls_open_in_editor(run_editor: mock.Mock) -> None:
    s1 = create_task("Story").task_id
    assert_invoke(app, ["add", s1, "Subtask", "--editor"])
    assert run_editor.call_count == 1


def test_add_editor_short_flag(run_editor: mock.Mock) -> None:
    s1 = create_task("Story").task_id
    assert_invoke(app, ["add", s1, "Subtask", "-e"])
    assert run_editor.call_count == 1


def test_add_editor_opens_md_file(run_editor: mock.Mock) -> None:
    s1 = create_task("Story").task_id
    assert_invoke(app, ["add", s1, "Subtask", "--editor"])
    opened_path: Path = run_editor.call_args[0][0]
    assert opened_path.suffix == ".md"


def test_add_editor_upgrades_inline_task_to_file(
    tasks_root: Path, run_editor: mock.Mock
) -> None:
    s1 = create_task("Story").task_id
    # s1 is a basic .md file before adding subtask with --editor
    assert next(tasks_root.glob(f"{s1}-*.md")).is_file()

    assert_invoke(app, ["add", s1, "Subtask", "--editor"])

    # s1 must have upgraded to extended (directory)
    story_dir = next(tasks_root.glob(f"{s1}-*/"))
    assert story_dir.is_dir()
    assert (story_dir / "README.md").exists()


def test_add_editor_subtask_has_own_file(
    tasks_root: Path, run_editor: mock.Mock
) -> None:
    s1 = create_task("Story").task_id
    add_subtask(s1, "First subtask")

    assert_invoke(app, ["add", s1, "Second subtask", "--editor"])

    story_dir = next(tasks_root.glob(f"{s1}-*/"))
    t02_files = list(story_dir.glob("*t02-*.md"))
    assert len(t02_files) == 1


def test_add_editor_opens_subtask_file(tasks_root: Path, run_editor: mock.Mock) -> None:
    s1 = create_task("Story").task_id
    assert_invoke(app, ["add", s1, "Subtask", "--editor"])

    opened_path: Path = run_editor.call_args[0][0]
    story_dir = next(tasks_root.glob(f"{s1}-*/"))
    t01_file = next(story_dir.glob("*t01-*.md"))
    assert opened_path == t01_file.resolve()


def test_add_editor_without_details_still_creates_file(
    tasks_root: Path, run_editor: mock.Mock
) -> None:
    s1 = create_task("Story").task_id
    assert_invoke(app, ["add", s1, "Inline-turned-file", "--editor"])

    story_dir = next(tasks_root.glob(f"{s1}-*/"))
    t01_files = list(story_dir.glob("*t01-*.md"))
    assert len(t01_files) == 1
    opened_path: Path = run_editor.call_args[0][0]
    assert opened_path.exists()


# ---------------------------------------------------------------------------
# Slug revalidation after editor (same as edit command)
# ---------------------------------------------------------------------------


def test_new_editor_slug_change_renames_file(
    tasks_root: Path, run_editor: mock.Mock
) -> None:
    def fake_open(path: Path) -> None:
        content = path.read_text()
        path.write_text(content.replace("slug: my-story", "slug: renamed-story"))

    run_editor.side_effect = fake_open
    assert_invoke(app, ["new", "My story", "--editor"])

    assert len(list(tasks_root.glob("s01-renamed-story.md"))) == 1
    assert len(list(tasks_root.glob("s01-my-story.md"))) == 0


def test_add_editor_slug_change_renames_file(
    tasks_root: Path, run_editor: mock.Mock
) -> None:
    s1 = create_task("Story").task_id

    def fake_open(path: Path) -> None:
        content = path.read_text()
        path.write_text(content.replace("slug: subtask", "slug: renamed-sub"))

    run_editor.side_effect = fake_open
    assert_invoke(app, ["add", s1, "Subtask", "--editor"])

    story_dir = next(tasks_root.glob(f"{s1}-*/"))
    assert len(list(story_dir.glob("*t01-renamed-sub.md"))) == 1
    assert len(list(story_dir.glob("*t01-subtask.md"))) == 0
