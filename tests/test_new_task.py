from pathlib import Path

from tasker.cli import app

from .helpers import assert_invoke


def test_add_simple_task() -> None:
    result = assert_invoke(app, ["new", "Simple task summary"])
    assert "Task s01-simple-task-summary created" in result.output
    assert Path("tasker/s01-simple-task-summary.md").exists()


def test_task_continious_numbering() -> None:
    assert_invoke(app, ["new", "first task"])

    result = assert_invoke(app, ["new", "second task"])
    assert "Task s02-second-task created" in result.output
    assert Path("tasker/s02-second-task.md").exists()


def test_add_task_file_contains_title() -> None:
    assert_invoke(app, ["new", "My important task"])
    content = Path("tasker/s01-my-important-task.md").read_text()
    assert "My important task" in content


def test_add_task_file_contains_pending_status() -> None:
    assert_invoke(app, ["new", "My important task"])
    content = Path("tasker/s01-my-important-task.md").read_text()
    assert "status: pending" in content


def test_add_task_with_description() -> None:
    assert_invoke(app, ["new", "My task", "--details", "Some details here"])
    content = Path("tasker/s01-my-task.md").read_text()
    assert "Some details here" in content


def test_add_task_title_is_capitalized() -> None:
    assert_invoke(app, ["new", "my task"])
    content = Path("tasker/s01-my-task.md").read_text()
    assert "# My task" in content


def test_add_task_without_description_has_no_placeholder() -> None:
    assert_invoke(app, ["new", "My task"])
    content = Path("tasker/s01-my-task.md").read_text()
    assert "None" not in content


def test_add_task_explicit_slug() -> None:
    result = assert_invoke(app, ["new", "My long task title", "--slug", "custom-slug"])
    assert "Task s01-custom-slug created" in result.output
    assert Path("tasker/s01-custom-slug.md").exists()


def test_add_task_explicit_slug_overrides_derived() -> None:
    assert_invoke(app, ["new", "My long task title", "--slug", "custom-slug"])
    assert not Path("tasker/s01-my-long-task-title.md").exists()


def test_add_detail_creates_directory() -> None:
    assert_invoke(app, ["new", "My task", "--extended"])
    assert Path("tasker/s01-my-task").is_dir()


def test_add_detail_creates_readme() -> None:
    assert_invoke(app, ["new", "My task", "--extended"])
    assert Path("tasker/s01-my-task/README.md").exists()


def test_add_detail_readme_contains_title() -> None:
    assert_invoke(app, ["new", "My task", "--extended"])
    content = Path("tasker/s01-my-task/README.md").read_text()
    assert "My task" in content


def test_add_detail_does_not_create_md_file() -> None:
    assert_invoke(app, ["new", "My task", "--extended"])
    assert not Path("tasker/s01-my-task.md").exists()


# ---------------------------------------------------------------------------
# s22t07: show root task list on 'new'
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
