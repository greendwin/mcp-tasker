import json
from pathlib import Path

import pytest

from tasker.cli import app
from tasker.parse import parse_task_file

from .helpers import GetTaskFile, add_subtask, assert_invoke, create_task

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def s1() -> str:
    return create_task("Story one").task_id


@pytest.fixture()
def s2() -> str:
    return create_task("Story two").task_id


# ---------------------------------------------------------------------------
# move --parent : basic cases
# ---------------------------------------------------------------------------


def test_move_inline_subtask_to_another_parent(s1: str, s2: str) -> None:
    t01 = add_subtask(s1, "Task A").task_id
    result = assert_invoke(app, ["move", t01, "--parent", s2])
    assert "moved" in result.output
    assert s2 in result.output


def test_move_file_subtask_to_another_parent(s1: str, s2: str) -> None:
    t01 = add_subtask(s1, "Task A", details="Has details").task_id
    result = assert_invoke(app, ["move", t01, "--parent", s2])
    assert "moved" in result.output


def test_move_root_task_under_another(s1: str, s2: str) -> None:
    result = assert_invoke(app, ["move", s1, "--parent", s2])
    assert "moved" in result.output
    assert s2 in result.output


def test_move_extended_subtask_to_another_parent(s1: str, s2: str) -> None:
    t01 = add_subtask(s1, "Parent task", details="Details").task_id
    add_subtask(t01, "Child", details="Nested details")
    result = assert_invoke(app, ["move", t01, "--parent", s2])
    assert "moved" in result.output


# ---------------------------------------------------------------------------
# move --root
# ---------------------------------------------------------------------------


def test_move_subtask_to_root(s1: str) -> None:
    t01 = add_subtask(s1, "Promote me").task_id
    result = assert_invoke(app, ["move", t01, "--root"])
    assert "moved" in result.output
    assert "root" in result.output


def test_move_inline_subtask_to_root_creates_file(s1: str, tasks_root: Path) -> None:
    """Moving an inline task to root must create a file (s09t06)."""
    t01 = add_subtask(s1, "Promote me").task_id
    assert_invoke(app, ["move", t01, "--root"])
    new_files = list(tasks_root.glob("s*-promote-me.md"))
    assert len(new_files) == 1


def test_move_file_subtask_to_root(s1: str) -> None:
    t01 = add_subtask(s1, "Promote me", details="Has content").task_id
    result = assert_invoke(app, ["move", t01, "--root"])
    assert "root" in result.output


def test_move_extended_subtask_to_root(s1: str) -> None:
    t01 = add_subtask(s1, "Container", details="Details").task_id
    add_subtask(t01, "Child A")
    add_subtask(t01, "Child B")
    result = assert_invoke(app, ["move", t01, "--root"])
    assert "root" in result.output


# ---------------------------------------------------------------------------
# ID recalculation
# ---------------------------------------------------------------------------


def test_renames_are_printed(s1: str, s2: str) -> None:
    t01 = add_subtask(s1, "Task").task_id
    result = assert_invoke(app, ["move", t01, "--parent", s2])
    # The old id and new id should both appear (renamed)
    assert t01 in result.output
    # new id is s2 + tNN
    assert f"{s2}t01" in result.output


def test_renames_deep_subtree(s1: str, s2: str) -> None:
    t01 = add_subtask(s1, "Level 1", details="D").task_id
    t0101 = add_subtask(t01, "Level 2").task_id
    result = assert_invoke(app, ["move", t01, "--parent", s2])
    assert t01 in result.output
    assert t0101 in result.output


def test_json_renames(s1: str, s2: str) -> None:
    t01 = add_subtask(s1, "Task").task_id
    result = assert_invoke(app, ["--json-output", "move", t01, "--parent", s2])
    data = json.loads(result.output)
    assert "renames" in data
    assert data["renames"][0]["old_id"] == t01
    assert "task_refs" in data


def test_json_move_to_root(s1: str) -> None:
    t01 = add_subtask(s1, "Task").task_id
    result = assert_invoke(app, ["--json-output", "move", t01, "--root"])
    data = json.loads(result.output)
    assert "renames" in data
    assert "task_refs" in data


# ---------------------------------------------------------------------------
# File cleanup
# ---------------------------------------------------------------------------


def test_old_basic_file_removed_after_move(s1: str, s2: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Task A", details="Details").task_id
    # find original file
    story_dir = next(tasks_root.glob(f"{s1}-*/"))
    old_file = next(story_dir.glob(f"{t01}-*.md"))
    assert old_file.exists()

    assert_invoke(app, ["move", t01, "--parent", s2])
    assert not old_file.exists()


def test_old_extended_dir_removed_after_move(
    s1: str, s2: str, tasks_root: Path
) -> None:
    t01 = add_subtask(s1, "Container", details="Details").task_id
    add_subtask(t01, "Child", details="Child details")
    story_dir = next(tasks_root.glob(f"{s1}-*/"))
    old_dir = next(story_dir.glob(f"{t01}-*/"))
    assert old_dir.is_dir()

    assert_invoke(app, ["move", t01, "--parent", s2])
    assert not old_dir.exists()


def test_old_extended_dir_with_user_data_not_removed(
    s1: str, s2: str, tasks_root: Path
) -> None:
    t01 = add_subtask(s1, "Container", details="Details").task_id
    add_subtask(t01, "Child", details="Child details")
    story_dir = next(tasks_root.glob(f"{s1}-*/"))
    old_dir = next(story_dir.glob(f"{t01}-*/"))

    # place a non-task file inside the extended directory
    user_file = old_dir / "notes.txt"
    user_file.write_text("user notes")

    result = assert_invoke(app, ["move", t01, "--parent", s2], expect_error=True)
    assert "non-task files" in result.output

    # user data must still be there
    assert user_file.exists()
    assert user_file.read_text() == "user notes"


def test_new_file_created_after_move(s1: str, s2: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Task A", details="Details").task_id
    assert_invoke(app, ["move", t01, "--parent", s2])
    # new file should be under s2's directory
    story_dir = next(tasks_root.glob(f"{s2}-*/"))
    new_files = list(story_dir.glob(f"{s2}t01-*.md"))
    assert len(new_files) == 1


def test_old_root_file_removed_when_moved_under_parent(
    s1: str, s2: str, get_task_file: GetTaskFile
) -> None:
    old_file = get_task_file(s1)
    assert old_file.exists()

    assert_invoke(app, ["move", s1, "--parent", s2])
    assert not old_file.exists()


def test_move_to_root_creates_root_file(s1: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Promote me", details="Content").task_id
    assert_invoke(app, ["move", t01, "--root"])
    # should be a new root task file
    # new root ID should be s03 or higher (s1=s01, s2 not created here but
    # we only have s1 in this test)
    new_files = list(tasks_root.glob("s*-promote-me.md"))
    assert len(new_files) == 1


# ---------------------------------------------------------------------------
# Parent subtask list updated
# ---------------------------------------------------------------------------


def test_old_parent_subtask_list_updated(
    s1: str, s2: str, get_task_file: GetTaskFile
) -> None:
    t01 = add_subtask(s1, "Mover").task_id
    add_subtask(s1, "Stayer")
    assert_invoke(app, ["move", t01, "--parent", s2])

    # old parent should only have "Stayer"
    story_file = get_task_file(s1)
    content = story_file.read_text()
    assert "Mover" not in content
    assert "Stayer" in content


def test_new_parent_subtask_list_updated(s1: str, s2: str, tasks_root: Path) -> None:
    add_subtask(s1, "Task A")
    assert_invoke(app, ["move", f"{s1}t01", "--parent", s2])

    # new parent should list the moved task (may be .md or dir/README.md)
    candidates = list(tasks_root.glob(f"{s2}-*"))
    assert len(candidates) == 1
    path = candidates[0]
    content = (path / "README.md").read_text() if path.is_dir() else path.read_text()
    assert f"{s2}t01" in content
    assert "Task A" in content


# ---------------------------------------------------------------------------
# Task content preserved after move
# ---------------------------------------------------------------------------


def test_moved_task_preserves_description(s1: str, s2: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Described task", details="Important details").task_id
    assert_invoke(app, ["move", t01, "--parent", s2])
    story_dir = next(tasks_root.glob(f"{s2}-*/"))
    new_file = next(story_dir.glob(f"{s2}t01-*.md"))
    parsed = parse_task_file(new_file)
    assert parsed.task.description == "Important details"


def test_moved_task_preserves_status(s1: str, s2: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Started task").task_id
    assert_invoke(app, ["start", t01])
    assert_invoke(app, ["move", t01, "--parent", s2])
    # parent may have been upgraded to extended (directory)
    candidates = list(tasks_root.glob(f"{s2}-*"))
    path = candidates[0]
    content = (path / "README.md").read_text() if path.is_dir() else path.read_text()
    assert "[~]" in content  # in-progress checkbox


def test_moved_task_preserves_inline_subtasks(
    s1: str, s2: str, tasks_root: Path
) -> None:
    t01 = add_subtask(s1, "Container", details="Details").task_id
    add_subtask(t01, "Child A")
    add_subtask(t01, "Child B")
    assert_invoke(app, ["move", t01, "--parent", s2])

    # s2 is now extended (directory) because it gained a file-backed subtask
    story_dir = next(tasks_root.glob(f"{s2}-*/"))
    assert story_dir.is_dir()
    # container is basic (inline subtasks only) — a .md file
    container_file = next(story_dir.glob(f"{s2}t01-*.md"))
    content = container_file.read_text()
    assert "Child A" in content
    assert "Child B" in content


def test_moved_extended_task_preserves_file_subtasks(
    s1: str, s2: str, tasks_root: Path
) -> None:
    t01 = add_subtask(s1, "Container", details="Details").task_id
    add_subtask(t01, "Child A", details="A details")
    add_subtask(t01, "Child B", details="B details")
    assert_invoke(app, ["move", t01, "--parent", s2])

    story_dir = next(tasks_root.glob(f"{s2}-*/"))
    container_dir = next(story_dir.glob(f"{s2}t01-*/"))
    assert container_dir.is_dir()
    readme = container_dir / "README.md"
    assert readme.exists()
    content = readme.read_text()
    assert "Child A" in content
    assert "Child B" in content


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------


def test_move_requires_flag(s1: str) -> None:
    t01 = add_subtask(s1, "Task").task_id
    result = assert_invoke(app, ["move", t01], expect_error=True)
    assert "--parent" in result.output or "--root" in result.output


def test_move_rejects_both_flags(s1: str, s2: str) -> None:
    t01 = add_subtask(s1, "Task").task_id
    result = assert_invoke(
        app, ["move", t01, "--parent", s2, "--root"], expect_error=True
    )
    assert "only one" in result.output.lower()


def test_move_root_to_root_is_idempotent(s1: str) -> None:
    result = assert_invoke(app, ["move", s1, "--root"])
    assert "already" in result.output.lower()


def test_move_under_self_fails(s1: str) -> None:
    result = assert_invoke(app, ["move", s1, "--parent", s1], expect_error=True)
    assert "itself" in result.output.lower()


def test_move_under_descendant_fails(s1: str) -> None:
    t01 = add_subtask(s1, "Child", details="Details").task_id
    result = assert_invoke(app, ["move", s1, "--parent", t01], expect_error=True)
    assert "descendant" in result.output.lower()


def test_move_to_same_parent_is_idempotent(s1: str) -> None:
    t01 = add_subtask(s1, "Child").task_id
    result = assert_invoke(app, ["move", t01, "--parent", s1])
    assert "already" in result.output.lower()


def test_move_nonexistent_task_fails() -> None:
    assert_invoke(app, ["move", "s99", "--root"], expect_error=True)


def test_move_nonexistent_parent_fails(s1: str) -> None:
    t01 = add_subtask(s1, "Task").task_id
    assert_invoke(app, ["move", t01, "--parent", "s99"], expect_error=True)


# ---------------------------------------------------------------------------
# JSON output for errors
# ---------------------------------------------------------------------------


def test_json_move_error(s1: str) -> None:
    result = assert_invoke(
        app, ["--json-output", "move", s1, "--parent", s1], expect_error=True
    )
    data = json.loads(result.output)
    assert "error" in data


def test_json_move_idempotent(s1: str) -> None:
    result = assert_invoke(app, ["--json-output", "move", s1, "--root"])
    data = json.loads(result.output)
    assert data.get("already") is True
    assert "task_refs" in data


# ---------------------------------------------------------------------------
# Source parent downgrade after move (s12t04)
# ---------------------------------------------------------------------------


def test_move_last_file_subtask_downgrades_source_to_basic(
    s1: str, s2: str, tasks_root: Path
) -> None:
    """Moving the only file-based subtask out should downgrade the source
    from extended (directory) to basic (single file)."""
    t01 = add_subtask(s1, "File task", details="Has details").task_id

    # Source is extended (directory)
    src_dirs = list(tasks_root.glob(f"{s1}-*/"))
    assert len(src_dirs) == 1
    assert src_dirs[0].is_dir()

    assert_invoke(app, ["move", t01, "--parent", s2])

    # Source should now be a basic file, not a directory
    src_files = list(tasks_root.glob(f"{s1}-*.md"))
    assert len(src_files) == 1
    assert src_files[0].is_file()

    # Old directory should be gone
    src_dirs_after = [p for p in tasks_root.glob(f"{s1}-*") if p.is_dir()]
    assert src_dirs_after == []


def test_move_one_of_two_file_subtasks_keeps_source_extended(
    s1: str, s2: str, tasks_root: Path
) -> None:
    """Moving one file subtask while another remains should keep
    the source as extended (directory)."""
    add_subtask(s1, "Task A", details="Details A")
    t02 = add_subtask(s1, "Task B", details="Details B").task_id

    assert_invoke(app, ["move", t02, "--parent", s2])

    # Source should still be extended (directory)
    src_dirs = [p for p in tasks_root.glob(f"{s1}-*") if p.is_dir()]
    assert len(src_dirs) == 1


def test_move_all_subtasks_downgrades_parent_to_inline(
    s1: str, s2: str, tasks_root: Path
) -> None:
    """Moving all subtasks from a parent without description should
    downgrade it to inline in its own parent (s09t0704)."""
    t01 = add_subtask(s1, "Container", details="Has text").task_id
    t0101 = add_subtask(t01, "Child").task_id

    # s1 is now extended (directory) because t01 has details
    story_dir = next(tasks_root.glob(f"{s1}-*/"))
    container_file = next(story_dir.glob(f"{t01}-*.md"))
    content = container_file.read_text()
    # Remove description so container can go inline after losing subtasks
    lines = content.split("\n")
    new_lines = [line for line in lines if line != "Has text"]
    container_file.write_text("\n".join(new_lines))

    # Move the only subtask out
    assert_invoke(app, ["move", t0101, "--parent", s2])

    # Container should now be inline in s1's subtask list
    # s1 should have downgraded from extended to basic (single file)
    story_file = next(tasks_root.glob(f"{s1}-*.md"))
    story_content = story_file.read_text()
    assert "Container" in story_content
    assert f"- [ ] {t01}: Container" in story_content


# ---------------------------------------------------------------------------
# Non-move commands must NOT downgrade extended tasks (s09t0705)
# ---------------------------------------------------------------------------


def test_done_does_not_downgrade_extended_to_basic(s1: str, tasks_root: Path) -> None:
    """Marking a subtask done must not collapse the parent directory."""
    t01 = add_subtask(s1, "Task A", details="Has details").task_id

    # s1 is extended (directory)
    src_dirs = list(tasks_root.glob(f"{s1}-*/"))
    assert len(src_dirs) == 1

    assert_invoke(app, ["done", t01])

    # s1 must still be a directory, not a flat file
    src_dirs_after = list(tasks_root.glob(f"{s1}-*/"))
    assert len(src_dirs_after) == 1
    assert src_dirs_after[0].is_dir()


def test_cancel_does_not_downgrade_extended_to_basic(s1: str, tasks_root: Path) -> None:
    """Cancelling a subtask must not collapse the parent directory."""
    t01 = add_subtask(s1, "Task A", details="Has details").task_id

    src_dirs = list(tasks_root.glob(f"{s1}-*/"))
    assert len(src_dirs) == 1

    assert_invoke(app, ["cancel", t01])

    src_dirs_after = list(tasks_root.glob(f"{s1}-*/"))
    assert len(src_dirs_after) == 1
    assert src_dirs_after[0].is_dir()


def test_start_does_not_downgrade_extended_to_basic(s1: str, tasks_root: Path) -> None:
    """Starting a subtask must not collapse the parent directory."""
    t01 = add_subtask(s1, "Task A", details="Has details").task_id

    src_dirs = list(tasks_root.glob(f"{s1}-*/"))
    assert len(src_dirs) == 1

    assert_invoke(app, ["start", t01])

    src_dirs_after = list(tasks_root.glob(f"{s1}-*/"))
    assert len(src_dirs_after) == 1
    assert src_dirs_after[0].is_dir()


def test_reset_does_not_downgrade_extended_to_basic(s1: str, tasks_root: Path) -> None:
    """Resetting a subtask must not collapse the parent directory."""
    t01 = add_subtask(s1, "Task A", details="Has details").task_id
    assert_invoke(app, ["start", t01])

    src_dirs = list(tasks_root.glob(f"{s1}-*/"))
    assert len(src_dirs) == 1

    assert_invoke(app, ["reset", t01])

    src_dirs_after = list(tasks_root.glob(f"{s1}-*/"))
    assert len(src_dirs_after) == 1
    assert src_dirs_after[0].is_dir()


def test_edit_does_not_downgrade_extended_to_basic(s1: str, tasks_root: Path) -> None:
    """Editing a subtask title must not collapse the parent directory."""
    t01 = add_subtask(s1, "Task A", details="Has details").task_id

    src_dirs = list(tasks_root.glob(f"{s1}-*/"))
    assert len(src_dirs) == 1

    assert_invoke(app, ["edit", t01, "--title", "Updated title"])

    src_dirs_after = list(tasks_root.glob(f"{s1}-*/"))
    assert len(src_dirs_after) == 1
    assert src_dirs_after[0].is_dir()


# ---------------------------------------------------------------------------
# Moved task itself downgrades to inline when eligible (s09t0706)
# ---------------------------------------------------------------------------


def test_move_root_task_without_description_becomes_inline(
    s2: str, tasks_root: Path
) -> None:
    """A root task with no description or subtasks should become inline
    when moved under another task."""
    s1 = create_task("Simple story").task_id  # file-based, no description, no subtasks

    assert_invoke(app, ["move", s1, "--parent", s2])

    # The moved task (now s2t01) must be inline — no separate file
    new_id = f"{s2}t01"
    assert not any(
        tasks_root.rglob(f"{new_id}-*.md")
    ), f"Expected {new_id} to be inline, but a file was found"

    # Must appear as an inline bullet inside s2's file
    s2_file = next(tasks_root.glob(f"{s2}-*.md"))
    s2_content = s2_file.read_text()
    assert f"{new_id}: Simple story" in s2_content


def test_move_root_task_with_description_stays_basic(s2: str, tasks_root: Path) -> None:
    """A root task WITH description must remain file-based after being moved."""
    s1 = create_task("Story with desc").task_id
    assert_invoke(app, ["edit", s1, "--details", "Important context"])

    assert_invoke(app, ["move", s1, "--parent", s2])

    new_id = f"{s2}t01"
    assert any(
        tasks_root.rglob(f"{new_id}-*.md")
    ), f"Expected {new_id} to remain file-based, but no file was found"


def test_move_basic_subtask_without_description_becomes_inline(
    s1: str, s2: str, tasks_root: Path
) -> None:
    """A basic (file-based) subtask whose description was later cleared
    should become inline when moved to another parent."""
    t01 = add_subtask(s1, "Transient task", details="Initial description").task_id

    # Manually clear the description from the file
    s1_dir = next(tasks_root.glob(f"{s1}-*/"))
    t01_file = next(s1_dir.glob(f"{t01}-*.md"))
    content = t01_file.read_text()
    cleared = "\n".join(
        line for line in content.splitlines() if line != "Initial description"
    )
    t01_file.write_text(cleared)

    assert_invoke(app, ["move", t01, "--parent", s2])

    new_id = f"{s2}t01"
    assert not any(
        tasks_root.rglob(f"{new_id}-*.md")
    ), f"Expected {new_id} to be inline after move, but a file was found"


def test_move_basic_subtask_with_description_stays_basic(
    s1: str, s2: str, tasks_root: Path
) -> None:
    """A basic (file-based) subtask with a non-empty description must
    remain file-based after the move."""
    t01 = add_subtask(s1, "Rich task", details="Keeps description").task_id

    assert_invoke(app, ["move", t01, "--parent", s2])

    new_id = f"{s2}t01"
    assert any(
        tasks_root.rglob(f"{new_id}-*.md")
    ), f"Expected {new_id} to remain file-based, but no file was found"


# ---------------------------------------------------------------------------
# Multiple args (s09t08)
# ---------------------------------------------------------------------------


def test_move_multiple_tasks_to_parent(s1: str, s2: str) -> None:
    t01 = add_subtask(s1, "Task A").task_id
    t02 = add_subtask(s1, "Task B").task_id
    result = assert_invoke(app, ["move", t01, t02, "--parent", s2])
    assert "moved" in result.output
    assert s2 in result.output


def test_move_multiple_tasks_to_root(s2: str) -> None:
    t01 = add_subtask(s2, "Task A").task_id
    t02 = add_subtask(s2, "Task B").task_id
    result = assert_invoke(app, ["move", t01, t02, "--root"])
    assert "moved" in result.output


def test_move_multiple_shows_single_preview(s1: str, s2: str) -> None:
    """Preview block should appear only once at the end, not per task."""
    add_subtask(s1, "Task A")
    add_subtask(s1, "Task B")
    add_subtask(s1, "Task C")
    result = assert_invoke(
        app, ["move", f"{s1}t01", f"{s1}t02", f"{s1}t03", "--parent", s2]
    )
    # The parent header (Story two) should appear exactly once in the preview
    assert result.output.count("Story two") == 1


# ---------------------------------------------------------------------------
# show parent task on move --parent
# ---------------------------------------------------------------------------


def test_move_parent_shows_new_parent(s1: str, s2: str) -> None:
    t01 = add_subtask(s1, "Task A").task_id
    result = assert_invoke(app, ["move", t01, "--parent", s2])
    assert "Story two" in result.output


def test_move_parent_shows_moved_task_in_parent(s1: str, s2: str) -> None:
    add_subtask(s1, "Task A")
    result = assert_invoke(app, ["move", f"{s1}t01", "--parent", s2])
    assert "Task A" in result.output


def test_move_parent_shows_existing_sibling(s1: str, s2: str) -> None:
    t01 = add_subtask(s1, "Task A").task_id
    add_subtask(s2, "Pre-existing")
    result = assert_invoke(app, ["move", t01, "--parent", s2])
    assert "Pre-existing" in result.output


def test_move_root_shows_root_list(s1: str, s2: str) -> None:
    t01 = add_subtask(s1, "Task A").task_id
    result = assert_invoke(app, ["move", t01, "--root"])
    assert "Task A" in result.output


def test_move_root_no_subtasks_in_list(s1: str) -> None:
    add_subtask(s1, "Task A")
    add_subtask(s1, "Task B")
    result = assert_invoke(app, ["move", f"{s1}t01", "--root"])
    # subtasks of s1 are not shown (flat root list only)
    assert "Task B" not in result.output


def test_move_parent_json_no_preview(s1: str, s2: str) -> None:
    import json as _json

    t01 = add_subtask(s1, "Task A").task_id
    result = assert_invoke(app, ["--json-output", "move", t01, "--parent", s2])
    data = _json.loads(result.output)
    assert "task_refs" in data
    assert "parent" not in data


# ---------------------------------------------------------------------------
# deep nested detach cleans ancestor directories
# ---------------------------------------------------------------------------


def test_move_deep_nested_cleans_ancestor_dirs(tasks_root: Path, s1: str) -> None:
    t01 = add_subtask(s1, "Mid task").task_id
    # file-based subtask makes s01t01 extended (directory-based)
    leaf = add_subtask(t01, "Leaf task", details="Some details").task_id
    # note: child of s01t01 is s01t0101 (digits appended directly)
    assert_invoke(app, ["move", leaf, "--root"])
    # all intermediate directories should be cleaned up
    leftover = [p for p in tasks_root.rglob("*") if p.is_dir()]
    dirs = [str(p.relative_to(tasks_root)) for p in leftover]
    assert dirs == [], f"Leftover directories: {dirs}"


def test_move_deep_nested_to_parent_cleans_dirs(
    tasks_root: Path, s1: str, s2: str
) -> None:
    t01 = add_subtask(s1, "Mid task").task_id
    leaf = add_subtask(t01, "Leaf task", details="Some details").task_id
    assert_invoke(app, ["move", leaf, "--parent", s2])
    # s01's intermediate directory should be cleaned up
    for p in tasks_root.rglob("*"):
        if p.is_dir():
            assert f"{s1}t01" not in p.name, f"Leftover directory: {p}"


def test_move_deep_nested_to_parent_keeps_dirs(
    tasks_root: Path, s1: str, s2: str
) -> None:
    t01 = add_subtask(s1, "Mid task").task_id
    leaf1 = add_subtask(t01, "Leaf task 1", details="Some details").task_id
    add_subtask(t01, "Leaf task 2", details="Some details").task_id
    assert_invoke(app, ["move", leaf1, "--parent", s2])
    # s01's intermediate directory should remain
    dirs = [p for p in tasks_root.rglob("*") if p.is_dir()]
    assert any(t01 in p.name for p in dirs), f"Missing {t01} dir"


# ---------------------------------------------------------------------------
# move --delete
# ---------------------------------------------------------------------------


def test_delete_inline_subtask(s1: str, get_task_file: GetTaskFile) -> None:
    add_subtask(s1, "Task A")
    add_subtask(s1, "Task B")
    result = assert_invoke(app, ["move", f"{s1}t01", "--delete"])
    assert "deleted" in result.output

    content = get_task_file(s1).read_text()
    assert "Task A" not in content
    assert "Task B" in content


def test_delete_file_subtask(s1: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Task A", details="Has details").task_id
    story_dir = next(tasks_root.glob(f"{s1}-*/"))
    old_file = next(story_dir.glob(f"{t01}-*.md"))
    assert old_file.exists()

    result = assert_invoke(app, ["move", t01, "--delete"])
    assert "deleted" in result.output
    assert not old_file.exists()


def test_delete_extended_subtask(s1: str, tasks_root: Path) -> None:
    t01 = add_subtask(s1, "Container", details="Details").task_id
    add_subtask(t01, "Child", details="Child details")
    story_dir = next(tasks_root.glob(f"{s1}-*/"))
    old_dir = next(story_dir.glob(f"{t01}-*/"))
    assert old_dir.is_dir()

    assert_invoke(app, ["move", t01, "--delete"])
    assert not old_dir.exists()


def test_delete_root_task(s1: str, tasks_root: Path) -> None:
    old_file = next(tasks_root.glob(f"{s1}-*.md"))
    assert old_file.exists()

    result = assert_invoke(app, ["move", s1, "--delete"])
    assert "deleted" in result.output
    assert not old_file.exists()


def test_delete_multiple_tasks(s1: str) -> None:
    add_subtask(s1, "Task A")
    add_subtask(s1, "Task B")
    result = assert_invoke(app, ["move", f"{s1}t01", f"{s1}t02", "--delete"])
    assert "deleted" in result.output


def test_delete_json_output(s1: str) -> None:
    add_subtask(s1, "Task A")
    result = assert_invoke(app, ["--json-output", "move", f"{s1}t01", "--delete"])
    data = json.loads(result.output)
    assert "task_refs" in data


def test_delete_parent_downgrades(s1: str, tasks_root: Path) -> None:
    """Deleting the only file-based subtask should downgrade parent."""
    t01 = add_subtask(s1, "File task", details="Has details").task_id

    src_dirs = list(tasks_root.glob(f"{s1}-*/"))
    assert len(src_dirs) == 1
    assert src_dirs[0].is_dir()

    assert_invoke(app, ["move", t01, "--delete"])

    # source should downgrade to basic file
    src_files = list(tasks_root.glob(f"{s1}-*.md"))
    assert len(src_files) == 1
    assert src_files[0].is_file()


def test_delete_rejects_with_parent_flag(s1: str, s2: str) -> None:
    t01 = add_subtask(s1, "Task").task_id
    result = assert_invoke(
        app, ["move", t01, "--delete", "--parent", s2], expect_error=True
    )
    assert "only one" in result.output.lower()


def test_delete_rejects_with_root_flag(s1: str) -> None:
    t01 = add_subtask(s1, "Task").task_id
    result = assert_invoke(app, ["move", t01, "--delete", "--root"], expect_error=True)
    assert "only one" in result.output.lower()


def test_delete_shows_preview_with_parent(s1: str) -> None:
    """Deleting a subtask should show the parent preview with deleted task."""
    add_subtask(s1, "Task A")
    add_subtask(s1, "Task B")
    result = assert_invoke(app, ["move", f"{s1}t01", "--delete"])
    # preview should show parent with remaining and deleted tasks
    assert "Story one" in result.output
    assert "Task A" in result.output
    assert "Task B" in result.output


def test_delete_preview_not_listed_as_subtask_text(s1: str) -> None:
    """No 'Deleted subtasks:' section — preview handles it."""
    add_subtask(s1, "Task A")
    result = assert_invoke(app, ["move", f"{s1}t01", "--delete"])
    assert "Deleted subtasks:" not in result.output
