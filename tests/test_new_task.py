from pathlib import Path

from tasker.cli import app

from .helpers import SetupTaskEdits, assert_invoke


def test_add_simple_task(tasks_root: Path) -> None:
    result = assert_invoke(app, ["new", "Simple task summary"])
    assert "Task s01-simple-task-summary created" in result.output
    assert (tasks_root / "s01-simple-task-summary.md").exists()


def test_task_continious_numbering(tasks_root: Path) -> None:
    assert_invoke(app, ["new", "first task"])

    result = assert_invoke(app, ["new", "second task"])
    assert "Task s02-second-task created" in result.output
    assert (tasks_root / "s02-second-task.md").exists()


def test_add_task_file_contains_title(tasks_root: Path) -> None:
    assert_invoke(app, ["new", "My important task"])
    content = (tasks_root / "s01-my-important-task.md").read_text()
    assert "My important task" in content


def test_add_task_file_contains_pending_status(tasks_root: Path) -> None:
    assert_invoke(app, ["new", "My important task"])
    content = (tasks_root / "s01-my-important-task.md").read_text()
    assert "status: pending" in content


def test_add_task_with_description(tasks_root: Path) -> None:
    assert_invoke(app, ["new", "My task", "--details", "Some details here"])
    content = (tasks_root / "s01-my-task.md").read_text()
    assert "Some details here" in content


def test_add_task_title_is_capitalized(tasks_root: Path) -> None:
    assert_invoke(app, ["new", "my task"])
    content = (tasks_root / "s01-my-task.md").read_text()
    assert "# My task" in content


def test_add_task_without_description_has_no_placeholder(tasks_root: Path) -> None:
    assert_invoke(app, ["new", "My task"])
    content = (tasks_root / "s01-my-task.md").read_text()
    assert "None" not in content


def test_add_task_explicit_slug(tasks_root: Path) -> None:
    result = assert_invoke(app, ["new", "My long task title", "--slug", "custom-slug"])
    assert "Task s01-custom-slug created" in result.output
    assert (tasks_root / "s01-custom-slug.md").exists()


def test_add_task_explicit_slug_overrides_derived(tasks_root: Path) -> None:
    assert_invoke(app, ["new", "My long task title", "--slug", "custom-slug"])
    assert not (tasks_root / "s01-my-long-task-title.md").exists()


def test_add_detail_creates_directory(tasks_root: Path) -> None:
    assert_invoke(app, ["new", "My task", "--extended"])
    assert (tasks_root / "s01-my-task").is_dir()


def test_add_detail_creates_readme(tasks_root: Path) -> None:
    assert_invoke(app, ["new", "My task", "--extended"])
    assert (tasks_root / "s01-my-task" / "README.md").exists()


def test_add_detail_readme_contains_title(tasks_root: Path) -> None:
    assert_invoke(app, ["new", "My task", "--extended"])
    content = (tasks_root / "s01-my-task" / "README.md").read_text()
    assert "My task" in content


def test_add_detail_does_not_create_md_file(tasks_root: Path) -> None:
    assert_invoke(app, ["new", "My task", "--extended"])
    assert not (tasks_root / "s01-my-task.md").exists()


# ---------------------------------------------------------------------------
# show root task list on 'new'
# ---------------------------------------------------------------------------


def test_new_shows_root_list() -> None:
    assert_invoke(app, ["new", "First task"])
    result = assert_invoke(app, ["new", "Second task"])
    assert "Second task" in result.output


def test_new_root_list_no_subtasks() -> None:
    assert_invoke(app, ["new", "Story"])
    assert_invoke(app, ["add", "s01", "Subtask A"])
    result = assert_invoke(app, ["new", "Another story"])
    # subtasks of s01 are not shown (flat root list only)
    assert "Subtask A" not in result.output


def test_new_json_no_root_list() -> None:
    import json as _json

    result = assert_invoke(app, ["--json-output", "new", "My task"])
    data = _json.loads(result.output)
    assert "task_ref" in data
    assert "First task" not in result.output


# ---------------------------------------------------------------------------
# s21: show actual slug after editor invoke
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# multi-word title without quotes
# ---------------------------------------------------------------------------


def test_new_multi_word_title(tasks_root: Path) -> None:
    result = assert_invoke(app, ["new", "Design", "file", "structure"])
    assert "Task s01-design-file-structure created" in result.output
    assert (tasks_root / "s01-design-file-structure.md").exists()


def test_new_multi_word_title_capitalized(tasks_root: Path) -> None:
    assert_invoke(app, ["new", "design", "file", "structure"])
    content = (tasks_root / "s01-design-file-structure.md").read_text()
    assert "# Design file structure" in content


def test_new_multi_word_with_options(tasks_root: Path) -> None:
    result = assert_invoke(app, ["new", "Design", "file", "structure", "--slug", "dfs"])
    assert "Task s01-dfs created" in result.output
    assert (tasks_root / "s01-dfs.md").exists()
    content = (tasks_root / "s01-dfs.md").read_text()
    assert "# Design file structure" in content


def test_new_single_word_still_works(tasks_root: Path) -> None:
    result = assert_invoke(app, ["new", "Design"])
    assert "Task s01-design created" in result.output


# ---------------------------------------------------------------------------
# s21: show actual slug after editor invoke
# ---------------------------------------------------------------------------


def test_new_editor_output_shows_updated_slug(
    setup_task_edits: SetupTaskEdits,
) -> None:
    setup_task_edits(("slug: my-task", "slug: renamed"))
    result = assert_invoke(app, ["new", "My task", "--editor"])
    assert "s01-renamed" in result.output
    assert "my-task" not in result.output
