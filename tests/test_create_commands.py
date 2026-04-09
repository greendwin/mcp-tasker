"""Tests for create commands: new, add, add-many, and --editor variants."""

import json
from pathlib import Path
from typing import Any
from unittest import mock

import pytest

from tasker.base_types import TaskStatus
from tasker.cli import app
from tasker.parse import parse_task_file

from .helpers import (
    GetTaskFile,
    SetupTaskEdits,
    add_subtask,
    assert_invoke,
    create_task,
)

# ---------------------------------------------------------------------------
# new command (from test_new_task.py)
# ---------------------------------------------------------------------------


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
    result = assert_invoke(app, ["--json-output", "new", "My task"])
    data = json.loads(result.output)
    assert "task_ref" in data
    assert "First task" not in result.output


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


def test_new_editor_output_shows_updated_slug(
    setup_task_edits: SetupTaskEdits,
) -> None:
    setup_task_edits(("slug: my-task", "slug: renamed"))
    result = assert_invoke(app, ["new", "My task", "--editor"])
    assert "s01-renamed" in result.output
    assert "my-task" not in result.output


# ---------------------------------------------------------------------------
# add command (from test_add_task.py)
# ---------------------------------------------------------------------------


@pytest.fixture()
def parent_id() -> str:
    return create_task("My story").task_id


def test_add_inline_subtask_output(parent_id: str) -> None:
    result = assert_invoke(app, ["add", parent_id, "Define task forms"])
    assert f"{parent_id}t01" in result.output


def test_add_shows_parent_title(parent_id: str) -> None:
    result = assert_invoke(app, ["add", parent_id, "Define task forms"])
    assert "My story" in result.output


def test_add_shows_parent_id(parent_id: str) -> None:
    result = assert_invoke(app, ["add", parent_id, "Define task forms"])
    assert parent_id in result.output


def test_add_shows_new_subtask_in_parent_view(parent_id: str) -> None:
    result = assert_invoke(app, ["add", parent_id, "Define task forms"])
    assert "Define task forms" in result.output


def test_add_second_subtask_shows_all_siblings(parent_id: str) -> None:
    add_subtask(parent_id, "First subtask")
    result = assert_invoke(app, ["add", parent_id, "Second subtask"])
    assert "First subtask" in result.output
    assert "Second subtask" in result.output


def test_add_subtask_file_contains_entry(
    parent_id: str, get_task_file: GetTaskFile
) -> None:
    assert_invoke(app, ["add", parent_id, "Define task forms"])
    task_file = get_task_file(parent_id)
    content = task_file.read_text()
    assert f"- [ ] {parent_id}t01: Define task forms" in content


def test_add_multiple_subtasks_increments_id(
    parent_id: str, get_task_file: GetTaskFile
) -> None:
    assert_invoke(app, ["add", parent_id, "First subtask"])
    result = assert_invoke(app, ["add", parent_id, "Second subtask"])
    assert f"{parent_id}t02" in result.output
    task_file = get_task_file(parent_id)
    content = task_file.read_text()
    assert f"- [ ] {parent_id}t01: First subtask" in content
    assert f"- [ ] {parent_id}t02: Second subtask" in content


def test_add_subtask_parent_not_found() -> None:
    assert_invoke(app, ["add", "s99", "Some task"], expect_error=True)


def test_add_subtask_strips_slug_from_parent_id(
    parent_id: str, get_task_file: GetTaskFile
) -> None:
    task_file = get_task_file(parent_id)
    slug_ref = task_file.stem  # e.g. "s01-my-story"
    result = assert_invoke(app, ["add", slug_ref, "Define task forms"])
    assert f"{parent_id}t01" in result.output


def test_add_subtask_title_is_capitalized(
    parent_id: str, get_task_file: GetTaskFile
) -> None:
    assert_invoke(app, ["add", parent_id, "define task forms"])
    task_file = get_task_file(parent_id)
    content = task_file.read_text()
    assert f"- [ ] {parent_id}t01: Define task forms" in content


def test_add_subtask_parse_roundtrip(
    parent_id: str, get_task_file: GetTaskFile
) -> None:
    assert_invoke(app, ["add", parent_id, "First subtask"])
    assert_invoke(app, ["add", parent_id, "Second subtask"])
    task_file = get_task_file(parent_id)
    result = parse_task_file(task_file)
    assert len(result.subtasks) == 2
    assert result.subtasks[0].id == f"{parent_id}t01"
    assert result.subtasks[0].title == "First subtask"
    assert result.subtasks[0].status == TaskStatus.PENDING
    assert result.subtasks[1].id == f"{parent_id}t02"
    assert result.subtasks[1].title == "Second subtask"


def test_add_subtask_to_done_parent_reopens_it(
    parent_id: str, get_task_file: GetTaskFile
) -> None:
    t01 = add_subtask(parent_id, "First subtask").task_id
    assert_invoke(app, ["done", t01])
    # parent is now done; adding a new subtask should reopen it
    assert_invoke(app, ["add", parent_id, "Second subtask"])
    task_file = get_task_file(parent_id)
    r = parse_task_file(task_file)
    assert r.task.status == TaskStatus.PENDING


def test_add_subtask_to_cancelled_parent_reopens_it(
    parent_id: str, get_task_file: GetTaskFile
) -> None:
    t01 = add_subtask(parent_id, "First subtask").task_id
    assert_invoke(app, ["cancel", t01])
    # parent is now cancelled; adding a new subtask should reopen it
    assert_invoke(app, ["add", parent_id, "Second subtask"])
    task_file = get_task_file(parent_id)
    task = parse_task_file(task_file).task
    assert task.status == TaskStatus.PENDING


def test_add_subtask_to_in_progress_parent_keeps_status(
    parent_id: str, get_task_file: GetTaskFile
) -> None:
    t01 = add_subtask(parent_id, "First subtask").task_id
    assert_invoke(app, ["start", t01])
    # parent is in-progress; adding another subtask keeps it in-progress
    assert_invoke(app, ["add", parent_id, "Second subtask"])
    task_file = get_task_file(parent_id)
    task = parse_task_file(task_file).task
    assert task.status == TaskStatus.IN_PROGRESS


def test_add_detailed_subtask_upgrades_parent(tasks_root: Path, parent_id: str) -> None:
    assert_invoke(
        app, ["add", parent_id, "Write CLI spec", "--details", "Cover all commands"]
    )
    # parent should be upgraded to extended (directory)
    parent_dir = next(tasks_root.glob(f"{parent_id}-*/"))
    assert parent_dir.is_dir()
    assert (parent_dir / "README.md").exists()


def test_add_detailed_subtask_creates_child_file(
    tasks_root: Path, parent_id: str
) -> None:
    assert_invoke(
        app, ["add", parent_id, "Write CLI spec", "--details", "Cover all commands"]
    )
    parent_dir = next(tasks_root.glob(f"{parent_id}-*/"))
    child_file = next(parent_dir.glob(f"{parent_id}t01-*.md"))
    assert child_file.exists()
    content = child_file.read_text()
    assert "Write CLI spec" in content
    assert "Cover all commands" in content


def test_add_detailed_subtask_removes_old_parent_file(
    parent_id: str, get_task_file: GetTaskFile
) -> None:
    old_file = get_task_file(parent_id)
    assert old_file.exists()
    assert_invoke(
        app, ["add", parent_id, "Write CLI spec", "--details", "Cover all commands"]
    )
    assert not old_file.exists()


def test_add_detailed_subtask_output(parent_id: str) -> None:
    result = assert_invoke(
        app, ["add", parent_id, "Write CLI spec", "--details", "Cover all commands"]
    )
    assert f"{parent_id}t01" in result.output


def test_add_detailed_subtask_with_slug(tasks_root: Path, parent_id: str) -> None:
    assert_invoke(
        app,
        [
            "add",
            parent_id,
            "Write CLI spec",
            "--details",
            "Cover all commands",
            "--slug",
            "cli-spec",
        ],
    )
    parent_dir = next(tasks_root.glob(f"{parent_id}-*/"))
    child_file = parent_dir / f"{parent_id}t01-cli-spec.md"
    assert child_file.exists()


def test_add_detailed_subtask_parent_readme_has_link(
    tasks_root: Path, parent_id: str
) -> None:
    assert_invoke(
        app, ["add", parent_id, "Write CLI spec", "--details", "Cover all commands"]
    )
    parent_dir = next(tasks_root.glob(f"{parent_id}-*/"))
    readme = (parent_dir / "README.md").read_text()
    assert f"[{parent_id}t01](" in readme


def test_add_inline_then_detailed_subtask(tasks_root: Path, parent_id: str) -> None:
    assert_invoke(app, ["add", parent_id, "First inline"])
    assert_invoke(
        app, ["add", parent_id, "Second detailed", "--details", "Description"]
    )
    parent_dir = next(tasks_root.glob(f"{parent_id}-*/"))
    readme = (parent_dir / "README.md").read_text()
    # inline subtask rendered without link
    assert f"- [ ] {parent_id}t01: First inline" in readme
    # detailed subtask rendered with link
    assert f"[{parent_id}t02](" in readme


def test_add_subtask_to_inline_upgrades_parent(
    tasks_root: Path, parent_id: str
) -> None:
    t01 = add_subtask(parent_id, "Inline task").task_id
    result = assert_invoke(app, ["add", t01, "Nested subtask"])
    assert f"{t01}01" in result.output
    # inline parent was upgraded to file-backed
    parent_dir = next(tasks_root.glob(f"{parent_id}-*/"))
    assert (parent_dir / f"{t01}-inline-task.md").exists()
    task = parse_task_file(parent_dir / f"{t01}-inline-task.md").task
    assert task.id == t01
    assert task.title == "Inline task"
    # child is listed as inline subtask
    subtasks = parse_task_file(parent_dir / f"{t01}-inline-task.md").subtasks
    assert len(subtasks) == 1
    assert subtasks[0].title == "Nested subtask"


def test_add_detailed_subtask_child_parses_correctly(
    tasks_root: Path, parent_id: str
) -> None:
    assert_invoke(
        app, ["add", parent_id, "Write CLI spec", "--details", "Cover all commands"]
    )
    parent_dir = next(tasks_root.glob(f"{parent_id}-*/"))
    child_file = next(parent_dir.glob(f"{parent_id}t01-*.md"))
    child = parse_task_file(child_file).task
    assert child.id == f"{parent_id}t01"
    assert child.title == "Write CLI spec"
    assert child.description == "Cover all commands"
    assert child.status == TaskStatus.PENDING


def test_add_to_inline_task(tasks_root: Path, parent_id: str) -> None:
    root = create_task("root task")
    inline_subtask = add_subtask(root.task_ref, "subtask")

    # root task should be a basic task
    assert (tasks_root / (root.task_ref + ".md")).exists()

    _ = add_subtask(inline_subtask.task_ref, "should not fail")

    # root should be upgraded to directory-based
    assert (tasks_root / root.task_ref).is_dir()


def test_add_multi_word_title(parent_id: str) -> None:
    result = assert_invoke(app, ["add", parent_id, "Define", "task", "forms"])
    assert f"{parent_id}t01" in result.output


def test_add_multi_word_title_in_parent(
    parent_id: str, get_task_file: GetTaskFile
) -> None:
    assert_invoke(app, ["add", parent_id, "Define", "task", "forms"])
    task_file = get_task_file(parent_id)
    content = task_file.read_text()
    assert f"- [ ] {parent_id}t01: Define task forms" in content


def test_add_multi_word_with_details(tasks_root: Path, parent_id: str) -> None:
    assert_invoke(
        app,
        ["add", parent_id, "Write", "CLI", "spec", "--details", "Cover all commands"],
    )
    parent_dir = next(tasks_root.glob(f"{parent_id}-*/"))
    child_file = next(parent_dir.glob(f"{parent_id}t01-*.md"))
    content = child_file.read_text()
    assert "Write CLI spec" in content
    assert "Cover all commands" in content


def test_add_editor_output_shows_updated_slug(
    parent_id: str, setup_task_edits: SetupTaskEdits
) -> None:
    setup_task_edits(("slug: my-subtask", "slug: renamed"))
    result = assert_invoke(
        app, ["add", parent_id, "My subtask", "--details", "d", "--editor"]
    )
    assert f"{parent_id}t01-renamed" in result.output
    assert "my-subtask" not in result.output


# ---------------------------------------------------------------------------
# add-many command (from test_batch_add.py)
# ---------------------------------------------------------------------------


@pytest.fixture()
def batch_parent_id() -> str:
    return create_task("Batch story").task_id


def test_batch_creates_single_task(
    batch_parent_id: str, get_task_file: GetTaskFile
) -> None:
    assert_invoke(app, ["add-many", batch_parent_id], input="First task\n\n")
    assert (
        f"- [ ] {batch_parent_id}t01: First task"
        in get_task_file(batch_parent_id).read_text()
    )


def test_batch_creates_multiple_tasks(
    batch_parent_id: str, get_task_file: GetTaskFile
) -> None:
    assert_invoke(app, ["add-many", batch_parent_id], input="Task one\nTask two\n\n")
    content = get_task_file(batch_parent_id).read_text()
    assert f"- [ ] {batch_parent_id}t01: Task one" in content
    assert f"- [ ] {batch_parent_id}t02: Task two" in content


def test_batch_titles_are_capitalized(
    batch_parent_id: str, get_task_file: GetTaskFile
) -> None:
    assert_invoke(app, ["add-many", batch_parent_id], input="lowercase title\n\n")
    assert "Lowercase title" in get_task_file(batch_parent_id).read_text()


def test_batch_stops_on_empty_line(
    batch_parent_id: str, get_task_file: GetTaskFile
) -> None:
    assert_invoke(app, ["add-many", batch_parent_id], input="First\n\nIgnored\n")
    content = get_task_file(batch_parent_id).read_text()
    assert f"{batch_parent_id}t01" in content
    assert "Ignored" not in content


def test_batch_stops_on_eof(batch_parent_id: str, get_task_file: GetTaskFile) -> None:
    assert_invoke(app, ["add-many", batch_parent_id], input="First\nSecond")
    content = get_task_file(batch_parent_id).read_text()
    assert f"{batch_parent_id}t01" in content
    assert f"{batch_parent_id}t02" in content


def test_batch_output_mentions_all_ids(batch_parent_id: str) -> None:
    result = assert_invoke(app, ["add-many", batch_parent_id], input="Alpha\nBeta\n\n")
    assert f"{batch_parent_id}t01" in result.output
    assert f"{batch_parent_id}t02" in result.output


def test_batch_shows_prompt(batch_parent_id: str) -> None:
    result = assert_invoke(app, ["add-many", batch_parent_id], input="Task\n\n")
    assert ">" in result.output


def test_batch_empty_input_shows_no_tasks_added(batch_parent_id: str) -> None:
    result = assert_invoke(app, ["add-many", batch_parent_id], input="\n")
    assert "No tasks added" in result.output


def test_batch_json_outputs_parent_ref(batch_parent_id: str) -> None:
    result = assert_invoke(
        app, ["--json-output", "add-many", batch_parent_id], input="A\nB\n\n"
    )
    data = json.loads(result.output.strip())
    assert "parent_ref" in data
    assert data["parent_ref"] == batch_parent_id


def test_batch_json_task_ids(batch_parent_id: str) -> None:
    result = assert_invoke(
        app, ["--json-output", "add-many", batch_parent_id], input="A\nB\n\n"
    )
    data = json.loads(result.output.strip())
    assert "task_refs" in data
    assert isinstance(data["task_refs"], list)
    assert data["task_refs"] == [f"{batch_parent_id}t01", f"{batch_parent_id}t02"]


def test_batch_json_output_is_only_json(batch_parent_id: str) -> None:
    result = assert_invoke(
        app, ["--json-output", "add-many", batch_parent_id], input="Task\n\n"
    )
    json.loads(result.output.strip())  # must not raise


def test_batch_json_no_prompt_in_output(batch_parent_id: str) -> None:
    result = assert_invoke(
        app, ["--json-output", "add-many", batch_parent_id], input="Task\n\n"
    )
    assert ">" not in result.output


def test_batch_json_empty_input_returns_empty_list(batch_parent_id: str) -> None:
    result = assert_invoke(
        app, ["--json-output", "add-many", batch_parent_id], input="\n"
    )
    data = json.loads(result.output.strip())
    assert data["task_refs"] == []


def test_batch_add_to_done_parent_reopens_it(
    batch_parent_id: str, get_task_file: GetTaskFile
) -> None:
    t01 = add_subtask(batch_parent_id, "First subtask").task_id
    assert_invoke(app, ["done", t01])
    # parent is now done; batch-adding should reopen it
    assert_invoke(app, ["add-many", batch_parent_id], input="New task\n\n")
    task = parse_task_file(get_task_file(batch_parent_id)).task
    assert task.status == TaskStatus.PENDING


# ---------------------------------------------------------------------------
# --editor variants (from test_create_editor.py)
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


# ---------------------------------------------------------------------------
# JSON output for new and add (from test_json_output.py)
# ---------------------------------------------------------------------------


def _parse_json(output: str) -> Any:
    return json.loads(output.strip())


def test_json_new_task_outputs_valid_json() -> None:
    result = assert_invoke(app, ["--json-output", "new", "My task"])
    _parse_json(result.output)  # must not raise


def test_json_new_task_is_single_object() -> None:
    result = assert_invoke(app, ["--json-output", "new", "My task"])
    data = _parse_json(result.output)
    assert isinstance(data, dict)


def test_json_new_task_ref_is_correct() -> None:
    result = assert_invoke(app, ["--json-output", "new", "My task"])
    data = _parse_json(result.output)
    assert "task_ref" in data
    assert data["task_ref"] == "s01-my-task"


def test_json_new_task_no_extra_output() -> None:
    result = assert_invoke(app, ["--json-output", "new", "My task"])
    # entire output must be parseable as a single JSON value
    _parse_json(result.output)
    assert "[green]" not in result.output
    assert "[blue]" not in result.output


def test_json_add_task_outputs_valid_json() -> None:
    assert_invoke(app, ["new", "Parent story"])
    result = assert_invoke(app, ["--json-output", "add", "s01", "Subtask"])
    _parse_json(result.output)  # must not raise


def test_json_add_task_is_single_object() -> None:
    assert_invoke(app, ["new", "Parent story"])
    result = assert_invoke(app, ["--json-output", "add", "s01", "Subtask"])
    data = _parse_json(result.output)
    assert isinstance(data, dict)


def test_json_add_task_ref_is_correct() -> None:
    assert_invoke(app, ["new", "Parent story"])
    result = assert_invoke(app, ["--json-output", "add", "s01", "Subtask"])
    data = _parse_json(result.output)
    assert "task_ref" in data
    assert data["task_ref"] == "s01t01"


def test_json_add_task_no_extra_output() -> None:
    assert_invoke(app, ["new", "Parent story"])
    result = assert_invoke(app, ["--json-output", "add", "s01", "Subtask"])
    _parse_json(result.output)
    assert "[green]" not in result.output
    assert "[blue]" not in result.output


def test_json_error_outputs_valid_json() -> None:
    result = assert_invoke(
        app, ["--json-output", "add", "s99", "Task"], expect_error=True
    )
    _parse_json(result.output)  # must not raise


def test_json_error_is_single_object() -> None:
    result = assert_invoke(
        app, ["--json-output", "add", "s99", "Task"], expect_error=True
    )
    data = _parse_json(result.output)
    assert isinstance(data, dict)


def test_json_error_contains_error_key() -> None:
    result = assert_invoke(
        app, ["--json-output", "add", "s99", "Task"], expect_error=True
    )
    data = _parse_json(result.output)
    assert "error" in data


def test_json_error_message_is_non_empty() -> None:
    result = assert_invoke(
        app, ["--json-output", "add", "s99", "Task"], expect_error=True
    )
    data = _parse_json(result.output)
    assert data["error"]


def test_json_error_exits_nonzero() -> None:
    result = assert_invoke(
        app, ["--json-output", "add", "s99", "Task"], expect_error=True
    )
    assert result.exit_code != 0


def test_json_error_no_plain_error_prefix() -> None:
    result = assert_invoke(
        app, ["--json-output", "add", "s99", "Task"], expect_error=True
    )
    assert "Error:" not in result.output


def test_json_debug_error_includes_traceback() -> None:
    result = assert_invoke(
        app, ["--json-output", "--debug", "add", "s99", "Task"], expect_error=True
    )
    data = _parse_json(result.output)
    assert "traceback" in data


def test_json_debug_error_traceback_non_empty() -> None:
    result = assert_invoke(
        app, ["--json-output", "--debug", "add", "s99", "Task"], expect_error=True
    )
    data = _parse_json(result.output)
    assert data["traceback"]


def test_json_no_debug_error_no_traceback() -> None:
    result = assert_invoke(
        app, ["--json-output", "add", "s99", "Task"], expect_error=True
    )
    data = _parse_json(result.output)
    assert "traceback" not in data


def test_json_error_contains_task_ref() -> None:
    result = assert_invoke(
        app, ["--json-output", "add", "s99", "Task"], expect_error=True
    )
    data = _parse_json(result.output)
    assert "task_ref" in data


def test_json_error_task_ref_is_non_empty() -> None:
    result = assert_invoke(
        app, ["--json-output", "add", "s99", "Task"], expect_error=True
    )
    data = _parse_json(result.output)
    assert data["task_ref"]


def test_json_error_task_ref_contains_task_id() -> None:
    result = assert_invoke(
        app, ["--json-output", "add", "s99", "Task"], expect_error=True
    )
    data = _parse_json(result.output)
    assert "s99" in data["task_ref"]
