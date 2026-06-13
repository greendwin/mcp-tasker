import json
import platform
import subprocess
from pathlib import Path
from typing import Protocol
from unittest import mock

import pytest

from tasker.cli import _helpers, app
from tasker.parse import parse_task_file

from .helpers import (
    GetTaskFile,
    SetupTaskEdits,
    add_subtask,
    assert_invoke,
    create_task,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def s1() -> str:
    return create_task("Story one").task_id


# ---------------------------------------------------------------------------
# Edit details
# ---------------------------------------------------------------------------


def test_edit_details_on_file_task(s1: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Task A", details="Old details").task_id
    assert_invoke(app, ["edit", t01, "--details", "New details"])

    story_dir = next(tasks_root.glob(f"{s1}-*/"))
    task_file = next(story_dir.glob(f"{t01}-*.md"))
    parsed = parse_task_file(task_file)
    assert parsed.task.description == "New details"


def test_edit_details_capitalizes_first_letter(s1: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Task A", details="old details").task_id
    assert_invoke(app, ["edit", t01, "--details", "new description"])

    story_dir = next(tasks_root.glob(f"{s1}-*/"))
    task_file = next(story_dir.glob(f"{t01}-*.md"))
    parsed = parse_task_file(task_file)
    assert parsed.task.description == "New description"


def test_edit_details_on_root_task(s1: str, get_task_file: GetTaskFile) -> None:
    assert_invoke(app, ["edit", s1, "--details", "Root description"])

    task_file = get_task_file(s1)
    parsed = parse_task_file(task_file)
    assert parsed.task.description == "Root description"


def test_edit_details_replaces_multi_section_body(
    s1: str, get_task_file: GetTaskFile
) -> None:
    task_file = get_task_file(s1)
    content = task_file.read_text()
    task_file.write_text(
        content + "\nLead paragraph.\n\n## Notes\n\nImportant note here.\n"
    )
    seeded = parse_task_file(task_file).task.description
    assert seeded is not None and "## Notes" in seeded

    assert_invoke(app, ["edit", s1, "--details", "Replacement body"])

    parsed = parse_task_file(task_file)
    assert parsed.task.description == "Replacement body"

    rendered = task_file.read_text()
    assert "## Notes" not in rendered
    assert "Important note here." not in rendered
    assert "Lead paragraph." not in rendered


def test_edit_details_upgrades_inline_task(
    s1: str, tasks_root: Path, get_task_file: GetTaskFile
) -> None:
    t01 = add_subtask(s1, "Inline task").task_id

    # before: parent is a basic .md file (no directory)
    old_file = get_task_file(s1)
    assert old_file.is_file()

    assert_invoke(app, ["edit", t01, "--details", "Now has details"])

    # after: parent upgraded to extended (directory with README.md)
    story_dir = next(tasks_root.glob(f"{s1}-*/"))
    assert story_dir.is_dir()
    assert (story_dir / "README.md").exists()

    # child is now file-backed
    task_file = next(story_dir.glob(f"{t01}-*.md"))
    parsed = parse_task_file(task_file)
    assert parsed.task.description == "Now has details"


# ---------------------------------------------------------------------------
# Edit title
# ---------------------------------------------------------------------------


def test_edit_title(s1: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Old title", details="Details").task_id
    assert_invoke(app, ["edit", t01, "--title", "new title"])

    story_dir = next(tasks_root.glob(f"{s1}-*/"))
    task_file = next(story_dir.glob(f"{t01}-*.md"))
    parsed = parse_task_file(task_file)
    assert parsed.task.title == "New title"  # auto-capitalized


def test_edit_title_on_inline_task(s1: str, get_task_file: GetTaskFile) -> None:
    t01 = add_subtask(s1, "Old title").task_id
    assert_invoke(app, ["edit", t01, "--title", "updated title"])

    task_file = get_task_file(s1)
    content = task_file.read_text()
    assert "Updated title" in content


def test_edit_title_updates_parent_subtask_list(s1: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Old title", details="Details").task_id
    assert_invoke(app, ["edit", t01, "--title", "brand new title"])

    # parent README should reference the new title
    story_dir = next(tasks_root.glob(f"{s1}-*/"))
    readme = story_dir / "README.md"
    content = readme.read_text()
    assert "Brand new title" in content


# ---------------------------------------------------------------------------
# Edit slug
# ---------------------------------------------------------------------------


def test_edit_slug(s1: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Task A", details="Details").task_id
    assert_invoke(app, ["edit", t01, "--slug", "new-slug"])

    story_dir = next(tasks_root.glob(f"{s1}-*/"))
    new_files = list(story_dir.glob(f"{t01}-new-slug.md"))
    assert len(new_files) == 1


def test_edit_slug_removes_old_file(s1: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Task A", details="Details").task_id
    story_dir = next(tasks_root.glob(f"{s1}-*/"))
    old_file = next(story_dir.glob(f"{t01}-*.md"))
    old_path = old_file.resolve()

    assert_invoke(app, ["edit", t01, "--slug", "renamed"])
    assert not old_path.exists()


def test_edit_slug_upgrades_inline_task_and_parent(
    s1: str, tasks_root: Path, get_task_file: GetTaskFile
) -> None:
    t01 = add_subtask(s1, "Inline task").task_id

    # before: parent is a basic .md file
    old_file = get_task_file(s1)
    assert old_file.is_file()

    assert_invoke(app, ["edit", t01, "--slug", "custom-slug"])

    # after: parent upgraded to extended (directory with README.md)
    story_dir = next(tasks_root.glob(f"{s1}-*/"))
    assert story_dir.is_dir()
    assert (story_dir / "README.md").exists()

    # child is now file-backed with the custom slug
    task_file = next(story_dir.glob(f"{t01}-custom-slug.md"))
    assert task_file.exists()


# ---------------------------------------------------------------------------
# Multiple fields at once
# ---------------------------------------------------------------------------


def test_edit_multiple_fields(s1: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Task A", details="Old details").task_id
    assert_invoke(
        app, ["edit", t01, "--title", "new title", "--details", "New details"]
    )

    story_dir = next(tasks_root.glob(f"{s1}-*/"))
    task_file = next(story_dir.glob(f"{t01}-*.md"))
    parsed = parse_task_file(task_file)
    assert parsed.task.title == "New title"
    assert parsed.task.description == "New details"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_edit_no_flags_opens_editor(s1: str, run_editor: mock.Mock) -> None:
    assert_invoke(app, ["edit", s1])
    assert run_editor.call_count == 1


def test_edit_nonexistent_task_fails() -> None:
    assert_invoke(app, ["edit", "s99", "--title", "X"], expect_error=True)


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------


def test_edit_json_output(s1: str) -> None:
    result = assert_invoke(app, ["--json-output", "edit", s1, "--title", "Updated"])
    data = json.loads(result.output)
    assert "task_ref" in data


def test_edit_json_error(s1: str) -> None:
    result = assert_invoke(app, ["--json-output", "edit", s1], expect_error=True)
    data = json.loads(result.output)
    assert "error" in data


# ---------------------------------------------------------------------------
# Editor
# ---------------------------------------------------------------------------


run_editor_orig = _helpers.run_editor


class SetupEditors(Protocol):
    def __call__(
        self, *, system: str | None = None, visual: str | None, editor: str | None
    ) -> mock.Mock: ...


@pytest.fixture
def setup_editors(monkeypatch: pytest.MonkeyPatch) -> SetupEditors:
    def callback(
        *, system: str | None = None, visual: str | None, editor: str | None
    ) -> mock.Mock:
        subprocess_run = mock.Mock(return_value=None)
        monkeypatch.setattr(subprocess, "run", subprocess_run)

        if system is not None:
            monkeypatch.setattr(platform, "system", lambda: system)

        if visual:
            monkeypatch.setenv("VISUAL", visual)
        else:
            monkeypatch.delenv("VISUAL", raising=False)

        if editor:
            monkeypatch.setenv("EDITOR", editor)
        else:
            monkeypatch.delenv("EDITOR", raising=False)

        return subprocess_run

    return callback


def test_edit_editor_uses_visual_env_var(s1: str, setup_editors: SetupEditors) -> None:
    subprocess_run = setup_editors(visual="emacs", editor="vim")

    run_editor_orig(Path(s1))
    subprocess_run.assert_called_once_with(["emacs", s1])


def test_edit_editor_uses_editor_env_var(s1: str, setup_editors: SetupEditors) -> None:
    subprocess_run = setup_editors(visual=None, editor="nano")

    run_editor_orig(Path(s1))
    subprocess_run.assert_called_once_with(["nano", s1])


def test_edit_editor_fallback_linux(s1: str, setup_editors: SetupEditors) -> None:
    subprocess_run = setup_editors(system="Linux", visual=None, editor=None)

    run_editor_orig(Path(s1))
    subprocess_run.assert_called_once_with(["vi", s1])


def test_edit_editor_fallback_windows(s1: str, setup_editors: SetupEditors) -> None:
    subprocess_run = setup_editors(system="Windows", visual=None, editor=None)

    run_editor_orig(Path(s1))
    subprocess_run.assert_called_once_with(["notepad", s1])


def test_edit_editor_alone_is_valid(s1: str, run_editor: mock.Mock) -> None:
    assert_invoke(app, ["edit", s1, "--editor"])
    assert run_editor.call_count == 1


def test_edit_editor_short_flag(s1: str, run_editor: mock.Mock) -> None:
    assert_invoke(app, ["edit", s1, "-e"])
    assert run_editor.call_count == 1


def test_edit_editor_opens_correct_file(s1: str, run_editor: mock.Mock) -> None:
    assert_invoke(app, ["edit", s1, "--editor"])
    opened_path = run_editor.call_args[0][0]
    assert str(opened_path).endswith(".md")


def test_edit_editor_upgrades_inline_task(
    s1: str, tasks_root: Path, run_editor: mock.Mock
) -> None:
    t01 = add_subtask(s1, "Inline task").task_id

    # before: s1 is a basic .md (no dir), t01 is inline
    old_file = next(tasks_root.glob(f"{s1}-*.md"))
    assert old_file.is_file()

    assert_invoke(app, ["edit", t01, "--editor"])

    # after: s1 upgraded to extended dir, t01 has its own file
    story_dir = next(tasks_root.glob(f"{s1}-*/"))
    assert story_dir.is_dir()
    assert (story_dir / "README.md").exists()
    task_filename = list(story_dir.glob(f"{t01}-*.md"))
    assert len(task_filename) == 1

    expected_path = story_dir / task_filename[0]
    run_editor.assert_called_once_with(expected_path)


def test_edit_editor_applies_changes_before_opening(
    s1: str, run_editor: mock.Mock
) -> None:
    opened_contents: list[str] = []

    def fake_open(path: Path) -> None:
        opened_contents.append(path.read_text())

    run_editor.side_effect = fake_open

    assert_invoke(app, ["edit", s1, "--title", "Changed title", "--editor"])

    assert len(opened_contents) == 1
    assert "Changed title" in opened_contents[0]


def test_edit_editor_combined_with_other_flags(
    s1: str, tasks_root: Path, run_editor: mock.Mock
) -> None:
    assert_invoke(app, ["edit", s1, "--title", "New title", "--editor"])

    task_file = next(tasks_root.glob(f"{s1}-*.md"))
    content = task_file.read_text()
    assert "New title" in content
    assert run_editor.call_count == 1


# editor receives correct path after --slug change
def test_edit_slug_with_editor_opens_renamed_file(
    s1: str, run_editor: mock.Mock
) -> None:
    assert_invoke(app, ["edit", s1, "--slug", "renamed", "--editor"])

    assert run_editor.call_count == 1
    opened_path = run_editor.call_args[0][0]
    assert "renamed" in str(opened_path)
    assert opened_path.exists()


def test_edit_subtask_slug_with_editor_opens_renamed_file(
    s1: str, run_editor: mock.Mock
) -> None:
    t01 = add_subtask(s1, "Sub", details="Desc").task_ref
    t01_id = t01.split("-")[0]

    assert_invoke(app, ["edit", t01_id, "--slug", "renamed-sub", "--editor"])

    assert run_editor.call_count == 1
    opened_path = run_editor.call_args[0][0]
    assert "renamed-sub" in str(opened_path)
    assert opened_path.exists()


# editor receives correct path when slug was changed externally
def test_edit_after_external_slug_change_opens_correct_file(
    s1: str, tasks_root: Path, run_editor: mock.Mock
) -> None:
    # Simulate external edit: change slug in frontmatter without renaming file
    task_file = next(tasks_root.glob(f"{s1}-*.md"))
    content = task_file.read_text()
    content = content.replace("slug: story-one", "slug: ext-renamed")
    task_file.write_text(content)

    assert_invoke(app, ["edit", s1])

    assert run_editor.call_count == 1
    opened_path = run_editor.call_args[0][0]
    assert "ext-renamed" in str(opened_path)
    assert opened_path.exists()


# ---------------------------------------------------------------------------
# Slug editing in editor
# ---------------------------------------------------------------------------


def test_edit_editor_file_contains_slug(
    s1: str, setup_task_edits: SetupTaskEdits
) -> None:
    opened_content = setup_task_edits()
    assert_invoke(app, ["edit", s1])

    assert len(opened_content) == 1
    assert "slug:" in opened_content[0]


def test_edit_editor_slug_change_renames_file(
    s1: str, tasks_root: Path, setup_task_edits: SetupTaskEdits
) -> None:
    setup_task_edits(("slug: story-one", "slug: renamed-story"))
    assert_invoke(app, ["edit", s1])

    new_files = list(tasks_root.glob(f"{s1}-renamed-story.md"))
    assert len(new_files) == 1
    old_files = list(tasks_root.glob(f"{s1}-story-one.md"))
    assert len(old_files) == 0


def test_edit_editor_slug_change_preserves_body_edits(
    s1: str, tasks_root: Path, setup_task_edits: SetupTaskEdits
) -> None:
    setup_task_edits(
        ("slug: story-one", "slug: new-slug"),
        ("# Story one", "# Edited title"),
    )
    assert_invoke(app, ["edit", s1])

    new_file = next(tasks_root.glob(f"{s1}-new-slug.md"))
    assert "Edited title" in new_file.read_text()


def test_editor_slug_change_in_parent(
    s1: str, tasks_root: Path, setup_task_edits: SetupTaskEdits
) -> None:
    s1 = create_task("story one").task_ref
    t01 = add_subtask(s1, "subtask", details="file-based").task_ref

    assert (tasks_root / s1 / f"{t01}.md").exists()
    setup_task_edits(("slug: story-one", "slug: new-slug"))
    assert_invoke(app, ["edit", s1])
    assert not (tasks_root / s1 / f"{t01}.md").exists()

    s1_mod = s1.replace("story-one", "new-slug")
    assert (tasks_root / s1_mod / f"{t01}.md").exists()


def test_editor_slug_change_in_non_root_parent(
    s1: str, tasks_root: Path, setup_task_edits: SetupTaskEdits
) -> None:
    s1 = create_task("story one").task_ref
    t01 = add_subtask(s1, "task", details="extended").task_ref
    t0102 = add_subtask(t01, "subtask", details="file-based").task_ref

    assert (tasks_root / s1 / t01 / f"{t0102}.md").exists()
    setup_task_edits(("slug: story-one", "slug: new-slug"))
    assert_invoke(app, ["edit", s1])
    assert not (tasks_root / s1 / t01 / f"{t0102}.md").exists()

    t01_mod = t01.replace("task", "new-slug")
    assert not (tasks_root / s1 / t01_mod / f"{t0102}.md").exists()


# ---------------------------------------------------------------------------
# show actual slug after editor invoke
# ---------------------------------------------------------------------------


def test_edit_output_shows_updated_slug(
    s1: str, setup_task_edits: SetupTaskEdits
) -> None:
    setup_task_edits(("slug: story-one", "slug: renamed"))
    result = assert_invoke(app, ["edit", s1])

    assert f"{s1.split('-')[0]}-renamed" in result.output
    assert "story-one" not in result.output


def test_edit_json_output_shows_updated_slug(
    s1: str, setup_task_edits: SetupTaskEdits
) -> None:
    setup_task_edits(("slug: story-one", "slug: renamed"))
    result = assert_invoke(app, ["--json-output", "edit", s1, "--editor"])

    data = json.loads(result.output)
    assert data["task_ref"] == f"{s1.split('-')[0]}-renamed"


# --- task preview after edit ---


def test_edit_shows_task_title_after_update(s1: str) -> None:
    result = assert_invoke(app, ["edit", s1, "--title", "New title"])
    assert "New title" in result.output


def test_edit_shows_description_after_update(s1: str) -> None:
    result = assert_invoke(app, ["edit", s1, "--details", "Some description"])
    assert "Some description" in result.output


def test_edit_json_does_not_show_preview(s1: str) -> None:
    result = assert_invoke(app, ["--json-output", "edit", s1, "--title", "New title"])
    data = json.loads(result.output)
    assert data["task_ref"]
    # preview text should not leak into JSON output
    assert "New title" not in data.get("preview", "")


# --- edit archived task ---


def test_edit_archived_task_does_not_unarchive(s1: str) -> None:
    assert_invoke(app, ["done", "--force", s1])
    assert_invoke(app, ["archive", s1])
    result = assert_invoke(app, ["edit", s1, "--title", "New title"])
    assert "Unarchiving" not in result.output
    assert "New title" in result.output


def test_edit_shows_recent_marker(s1: str) -> None:
    assert_invoke(app, ["start", s1])
    result = assert_invoke(app, ["edit", s1, "--title", "Updated"])
    assert "(q)" in result.output


def test_edit_shows_body_sections(s1: str, get_task_file: GetTaskFile) -> None:
    task_file = get_task_file(s1)
    content = task_file.read_text()
    task_file.write_text(content + "\n## Notes\n\nImportant note here.\n")
    result = assert_invoke(app, ["edit", s1, "--title", "Updated"])
    assert "Important note here." in result.output
