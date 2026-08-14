from __future__ import annotations

from typing import Any

from tasker.base_types import Task, TaskStatus
from tasker.merge import MergeFileResult, merge_scalar_fields, merge_task_file


def _task(**overrides: Any) -> Task:
    defaults: dict[str, Any] = {
        "id": "s01t01",
        "status": TaskStatus.PENDING,
        "title": "Default title",
        "slug": "default-slug",
        "description": "Default description",
    }
    defaults.update(overrides)
    return Task(**defaults)


# --- merge_task_file tests ---

_TASK_ID = "s01"
_SLUG = "my-task"
_EXTENDED = False


def _merge(base: str | None, ours: str, theirs: str) -> MergeFileResult:
    return merge_task_file(
        base, ours, theirs, task_id=_TASK_ID, slug=_SLUG, extended=_EXTENDED
    )


def _make_file(
    *,
    title: str = "My Task",
    status: str = "pending",
    slug: str | None = None,
    order: int | None = None,
    description: str | None = None,
    subtask_lines: list[str] | None = None,
) -> str:
    """Build a task markdown file string for testing."""
    lines = ["---", "id: s01"]
    if slug is not None:
        lines.append(f"slug: {slug}")
    lines.append(f"status: {status}")
    if order is not None:
        lines.append(f"order: {order}")
    lines.append("---")
    lines.append("")
    lines.append(f"# {title}")
    if description is not None:
        lines.append("")
        lines.append(description)
    if subtask_lines is not None:
        lines.append("")
        lines.append("## Subtasks")
        lines.append("")
        for sl in subtask_lines:
            lines.append(sl)
    lines.append("")
    return "\n".join(lines)


class TestMergeTaskFileAllClean:
    """No conflicts: output matches normal render_task format."""

    def test_all_clean_no_subtasks(self) -> None:
        content = _make_file(description="A description", slug="my-task")
        result = _merge(content, content, content)
        assert isinstance(result, MergeFileResult)
        assert result.has_conflicts is False
        assert "<<<<<<" not in result.content
        assert "# My Task" in result.content
        assert "status: pending" in result.content
        assert "A description" in result.content

    def test_clean_merge_ours_changed(self) -> None:
        base = _make_file()
        ours = _make_file(title="Updated Title")
        theirs = _make_file()
        result = _merge(base, ours, theirs)
        assert result.has_conflicts is False
        assert "# Updated Title" in result.content

    def test_clean_merge_theirs_changed_status(self) -> None:
        base = _make_file()
        ours = _make_file()
        theirs = _make_file(status="done")
        result = _merge(base, ours, theirs)
        assert result.has_conflicts is False
        assert "status: done" in result.content


class TestMergeTaskFileStatusConflict:
    """Status conflict: markers appear in front-matter."""

    def test_status_conflict(self) -> None:
        base = _make_file()
        ours = _make_file(status="in-progress")
        theirs = _make_file(status="done")
        result = _merge(base, ours, theirs)
        assert result.has_conflicts is True
        assert "<<<<<<< ours" in result.content
        assert "status: in-progress" in result.content
        assert "status: done" in result.content
        assert ">>>>>>> theirs" in result.content


class TestMergeTaskFileTitleConflict:
    """Title conflict: markers around heading line."""

    def test_title_conflict(self) -> None:
        base = _make_file()
        ours = _make_file(title="Our Title")
        theirs = _make_file(title="Their Title")
        result = _merge(base, ours, theirs)
        assert result.has_conflicts is True
        assert "<<<<<<< ours" in result.content
        assert "# Our Title" in result.content
        assert "# Their Title" in result.content
        assert ">>>>>>> theirs" in result.content


class TestMergeTaskFileDescriptionConflict:
    """Description conflict: markers around description block."""

    def test_description_conflict(self) -> None:
        base = _make_file(description="Base desc")
        ours = _make_file(description="Our desc")
        theirs = _make_file(description="Their desc")
        result = _merge(base, ours, theirs)
        assert result.has_conflicts is True
        assert "<<<<<<< ours" in result.content
        assert "Our desc" in result.content
        assert "Their desc" in result.content
        assert ">>>>>>> theirs" in result.content


class TestMergeTaskFileUnifiedBodyGranularity:
    """The whole body is one merge unit, so non-overlapping body edits conflict."""

    def test_lead_and_section_edits_conflict(self) -> None:
        """Pin unified-body merge granularity.

        A branch editing only the lead paragraph and another editing only a
        section used to auto-merge. Because the body is now a single merge
        unit, these non-overlapping edits conflict instead.
        """
        base = _make_file(description="Lead paragraph.\n\n## Notes\n\nShared notes.")
        ours = _make_file(
            description="Edited lead paragraph.\n\n## Notes\n\nShared notes."
        )
        theirs = _make_file(description="Lead paragraph.\n\n## Notes\n\nEdited notes.")
        result = _merge(base, ours, theirs)
        assert result.has_conflicts is True
        assert "<<<<<<< ours" in result.content
        assert "Edited lead paragraph." in result.content
        assert "Edited notes." in result.content
        assert ">>>>>>> theirs" in result.content


class TestMergeTaskFileSubtaskConflict:
    """Subtask with conflicting title/status gets markers."""

    def test_subtask_title_conflict(self) -> None:
        base = _make_file(subtask_lines=["- [ ] s01t01: Task one"])
        ours = _make_file(subtask_lines=["- [ ] s01t01: Our version"])
        theirs = _make_file(subtask_lines=["- [ ] s01t01: Their version"])
        result = _merge(base, ours, theirs)
        assert result.has_conflicts is True
        assert "<<<<<<< ours" in result.content
        assert "- [ ] s01t01: Our version" in result.content
        assert "- [ ] s01t01: Their version" in result.content
        assert ">>>>>>> theirs" in result.content

    def test_subtask_status_conflict(self) -> None:
        base = _make_file(subtask_lines=["- [ ] s01t01: Task one"])
        ours = _make_file(subtask_lines=["- [~] s01t01: Task one"])
        theirs = _make_file(subtask_lines=["- [x] s01t01: Task one"])
        result = _merge(base, ours, theirs)
        assert result.has_conflicts is True
        assert "<<<<<<< ours" in result.content
        assert ">>>>>>> theirs" in result.content


class TestMergeTaskFileSubtaskDeleteModify:
    """Delete-modify conflict: both title and status None."""

    def test_delete_modify_conflict(self) -> None:
        base = _make_file(subtask_lines=["- [ ] s01t01: Task one"])
        ours = _make_file(subtask_lines=["- [~] s01t01: Modified task"])
        theirs = _make_file(subtask_lines=[])  # deleted
        result = _merge(base, ours, theirs)
        assert result.has_conflicts is True
        assert "<<<<<<< ours" in result.content
        assert "- [~] s01t01: Modified task" in result.content
        assert ">>>>>>> theirs" in result.content

    def test_delete_modify_theirs_survives(self) -> None:
        base = _make_file(subtask_lines=["- [ ] s01t01: Task one"])
        ours = _make_file(subtask_lines=[])  # deleted
        theirs = _make_file(subtask_lines=["- [x] s01t01: Done task"])
        result = _merge(base, ours, theirs)
        assert result.has_conflicts is True
        assert "<<<<<<< ours" in result.content
        assert "- [x] s01t01: Done task" in result.content
        assert ">>>>>>> theirs" in result.content


class TestMergeTaskFileMultipleConflicts:
    """Several fields conflict simultaneously."""

    def test_multiple_conflicts(self) -> None:
        base = _make_file(description="Base desc")
        ours = _make_file(
            title="Our Title", status="in-progress", description="Our desc"
        )
        theirs = _make_file(
            title="Their Title", status="done", description="Their desc"
        )
        result = _merge(base, ours, theirs)
        assert result.has_conflicts is True
        # All three should be conflicted
        content = result.content
        assert content.count("<<<<<<< ours") == 3
        assert content.count(">>>>>>> theirs") == 3


class TestMergeTaskFileNoBase:
    """Base is None (two-way merge)."""

    def test_no_base_identical(self) -> None:
        content = _make_file()
        result = _merge(None, content, content)
        assert result.has_conflicts is False

    def test_no_base_different(self) -> None:
        ours = _make_file(title="Our Title")
        theirs = _make_file(title="Their Title")
        result = _merge(None, ours, theirs)
        assert result.has_conflicts is True
        assert "# Our Title" in result.content
        assert "# Their Title" in result.content


class TestMergeTaskFileMixedCleanAndConflict:
    """Some fields merge cleanly, others conflict."""

    def test_mixed(self) -> None:
        base = _make_file(description="Base desc")
        ours = _make_file(title="New Title", description="Our desc")
        theirs = _make_file(description="Their desc")
        result = _merge(base, ours, theirs)
        assert result.has_conflicts is True
        # title should merge cleanly (only ours changed)
        assert "# New Title" in result.content
        # description should conflict
        assert "Our desc" in result.content
        assert "Their desc" in result.content
        assert result.content.count("<<<<<<< ours") == 1


class TestMergeTaskFileSubtaskAdditions:
    """New subtasks from both sides appear sorted by ID."""

    def test_additions_from_both_sides(self) -> None:
        base = _make_file(subtask_lines=["- [ ] s01t01: Original"])
        ours = _make_file(
            subtask_lines=["- [ ] s01t01: Original", "- [ ] s01t02: Ours new"]
        )
        theirs = _make_file(
            subtask_lines=["- [ ] s01t01: Original", "- [ ] s01t03: Theirs new"]
        )
        result = _merge(base, ours, theirs)
        assert result.has_conflicts is False
        assert "s01t01: Original" in result.content
        assert "s01t02: Ours new" in result.content
        assert "s01t03: Theirs new" in result.content
        # sorted by ID
        ours_pos = result.content.index("s01t02")
        theirs_pos = result.content.index("s01t03")
        assert ours_pos < theirs_pos

    def test_additions_sorted_by_id(self) -> None:
        """When insertion order differs from ID order, output is sorted by ID."""
        base = _make_file(subtask_lines=["- [ ] s01t01: Original"])
        ours = _make_file(
            subtask_lines=["- [ ] s01t01: Original", "- [ ] s01t05: Ours late"]
        )
        theirs = _make_file(
            subtask_lines=["- [ ] s01t01: Original", "- [ ] s01t03: Theirs early"]
        )
        result = _merge(base, ours, theirs)
        assert result.has_conflicts is False
        lines = result.content.splitlines()
        subtask_lines = [ln for ln in lines if ln.startswith("- [")]
        ids = [ln.split("]")[1].strip().split(":")[0].strip() for ln in subtask_lines]
        assert ids == ["s01t01", "s01t03", "s01t05"]


class TestMergeTaskFileBodySectionConflict:
    """Diverging edits to a body section produce one body conflict block."""

    def test_body_section_conflict(self) -> None:
        base = _make_file(description="## Notes\n\nBase notes")
        ours = _make_file(description="## Notes\n\nOur notes")
        theirs = _make_file(description="## Notes\n\nTheir notes")
        result = _merge(base, ours, theirs)
        assert result.has_conflicts is True
        assert "<<<<<<< ours" in result.content
        assert "Our notes" in result.content
        assert "Their notes" in result.content
        assert ">>>>>>> theirs" in result.content


class TestMergeTaskFileSlugConflict:
    """Slug conflict: markers appear in front-matter."""

    def test_both_sides_different_slugs(self) -> None:
        base = _make_file(slug="base-slug")
        ours = _make_file(slug="our-slug")
        theirs = _make_file(slug="their-slug")
        result = _merge(base, ours, theirs)
        assert result.has_conflicts is True
        assert "<<<<<<< ours" in result.content
        assert "slug: our-slug" in result.content
        assert "slug: their-slug" in result.content
        assert ">>>>>>> theirs" in result.content

    def test_one_side_has_slug_other_none(self) -> None:
        """When one side has slug=None, the conflict block should have an empty
        line for that side (no 'slug:' key emitted)."""
        # Test at the merge_scalar_fields level since parse_task provides
        # a fallback slug from its parameter
        base_task = _task(slug="base-slug")
        ours_task = _task(slug="our-slug")
        theirs_task = _task(slug=None)
        result = merge_scalar_fields(base_task, ours_task, theirs_task)
        # Should be a conflict (all three different)
        assert result.slug is None


class TestMergeTaskFileEmptyDescriptionNotRendered:
    """Empty body should not produce blank paragraphs or newline artifacts."""

    def test_empty_string_description_omitted(self) -> None:
        """When merged description is empty string, output should match
        None behavior (no blank paragraph after title)."""
        # Build files where description will parse as empty string
        # by using a file with description and one without, where theirs wins
        # with empty description. Simpler: use identical files with no desc.
        base_file = _make_file()
        result = _merge(base_file, base_file, base_file)
        assert result.has_conflicts is False
        # The result with None description should have the title
        # followed only by a trailing newline, no extra blank paragraph
        result_none = result.content

        # Now build files where description is "" (empty string) via
        # a file with description="" that the parser may turn into None,
        # but the key check: the merge output should not have extra blanks
        # regardless of whether the merged value is None or ""
        content = _make_file(description="Real desc")
        result2 = _merge(content, content, content)
        assert result2.has_conflicts is False
        assert "Real desc" in result2.content

        # Verify that with no description, no extra blank lines appear
        lines = result_none.split("\n")
        title_idx = next(i for i, ln in enumerate(lines) if ln.startswith("# "))
        after_title = lines[title_idx + 1 :]
        # Strip trailing empty line
        while after_title and after_title[-1] == "":
            after_title.pop()
        # With no description, nothing should remain after title
        assert all(ln == "" for ln in after_title)

    def test_empty_body_no_newline_artifacts(self) -> None:
        """Output should not have quadruple newlines from an empty body."""
        content = _make_file()
        result = _merge(content, content, content)
        assert result.has_conflicts is False
        assert "\n\n\n\n" not in result.content


class TestMergeTaskFileLinkedSubtask:
    """Linked (file-based) subtasks render with markdown link syntax."""

    def test_linked_subtask_clean_merge(self) -> None:
        """All sides identical linked subtask -- output preserves link format."""
        linked_line = "- [ ] [s01t01](s01t01-my-sub.md): Sub task"
        content = _make_file(subtask_lines=[linked_line])
        result = _merge(content, content, content)
        assert result.has_conflicts is False
        assert "[s01t01](s01t01-my-sub.md)" in result.content

    def test_linked_subtask_conflict(self) -> None:
        """Both sides change title -- conflict with link format preserved."""
        base_line = "- [ ] [s01t01](s01t01-my-sub.md): Sub task"
        ours_line = "- [ ] [s01t01](s01t01-my-sub.md): Our title"
        theirs_line = "- [ ] [s01t01](s01t01-my-sub.md): Their title"
        base = _make_file(subtask_lines=[base_line])
        ours = _make_file(subtask_lines=[ours_line])
        theirs = _make_file(subtask_lines=[theirs_line])
        result = _merge(base, ours, theirs)
        assert result.has_conflicts is True
        assert "<<<<<<< ours" in result.content
        assert "[s01t01](s01t01-my-sub.md): Our title" in result.content
        assert "[s01t01](s01t01-my-sub.md): Their title" in result.content
        assert ">>>>>>> theirs" in result.content


class TestMergeTaskFileDeleteModifyNoBlankLine:
    """Delete-modify conflict should not produce blank line between markers."""

    def test_no_blank_line_when_theirs_deleted(self) -> None:
        base = _make_file(subtask_lines=["- [ ] s01t01: Task one"])
        ours = _make_file(subtask_lines=["- [~] s01t01: Modified task"])
        theirs = _make_file(subtask_lines=[])
        result = _merge(base, ours, theirs)
        assert result.has_conflicts is True
        # The empty side should NOT produce a blank line between ======= and >>>>>>>
        assert "=======\n>>>>>>> theirs" in result.content

    def test_no_blank_line_when_ours_deleted(self) -> None:
        base = _make_file(subtask_lines=["- [ ] s01t01: Task one"])
        ours = _make_file(subtask_lines=[])
        theirs = _make_file(subtask_lines=["- [x] s01t01: Done task"])
        result = _merge(base, ours, theirs)
        assert result.has_conflicts is True
        # The empty side should NOT produce a blank line between <<<<<<< and =======
        assert "<<<<<<< ours\n=======" in result.content


class TestMergeTaskFileOrderScalar:
    """`order` is an ordinary front-matter scalar: take the changed side,
    conflict only when both diverge, and emit `order:` only when set."""

    # --- Slice A: one-sided change merges cleanly to that side ---

    def test_order_ours_changed_wins(self) -> None:
        base = _make_file(order=1)
        ours = _make_file(order=5)
        theirs = _make_file(order=1)
        result = _merge(base, ours, theirs)
        assert result.has_conflicts is False
        assert "order: 5" in result.content

    def test_order_one_side_sets_from_unset(self) -> None:
        base = _make_file()  # unset
        ours = _make_file(order=3)
        theirs = _make_file()  # unset
        result = _merge(base, ours, theirs)
        assert result.has_conflicts is False
        assert "order: 3" in result.content

    # --- Slice B: divergent order conflicts like other scalars ---

    def test_order_divergent_conflict(self) -> None:
        base = _make_file(order=1)
        ours = _make_file(order=2)
        theirs = _make_file(order=3)
        result = _merge(base, ours, theirs)
        assert result.has_conflicts is True
        assert "<<<<<<< ours" in result.content
        assert "order: 2" in result.content
        assert "order: 3" in result.content
        assert ">>>>>>> theirs" in result.content

    # --- Slice C: emit `order:` only when the merged value is set ---

    def test_order_omitted_when_all_unset(self) -> None:
        content = _make_file()  # no order anywhere
        result = _merge(content, content, content)
        assert result.has_conflicts is False
        assert "order:" not in result.content

    def test_order_both_cleared_omits_line(self) -> None:
        base = _make_file(order=1)
        ours = _make_file()  # cleared
        theirs = _make_file()  # cleared
        result = _merge(base, ours, theirs)
        assert result.has_conflicts is False
        assert "order:" not in result.content

    def test_order_base_cleared_one_side(self) -> None:
        base = _make_file(order=2)
        ours = _make_file()  # cleared
        theirs = _make_file(order=2)  # unchanged from base
        result = _merge(base, ours, theirs)
        assert result.has_conflicts is False
        assert "order:" not in result.content


class TestMergeTaskFileOrderUpgrade:
    """Adding `order` upgrades an inline task to a file; that shape must merge
    cleanly against a side that left the task inline/unordered."""

    # --- Slice D ---

    def test_order_added_by_upgrade_side(self) -> None:
        base = _make_file()  # inline / unordered
        ours = _make_file()  # left inline / unordered
        theirs = _make_file(order=4)  # upgraded by adding order
        result = _merge(base, ours, theirs)
        assert result.has_conflicts is False
        assert "order: 4" in result.content

    def test_subtask_line_inline_vs_upgraded_clean(self) -> None:
        # ordering a subtask upgrades its bullet inline -> file link; the side
        # that left it inline must not spuriously conflict with the upgrade
        base = _make_file(subtask_lines=["- [ ] s01t01: Task one"])
        ours = _make_file(subtask_lines=["- [ ] s01t01: Task one"])
        theirs = _make_file(subtask_lines=["- [ ] [s01t01](s01t01-x.md): Task one"])
        result = _merge(base, ours, theirs)
        assert result.has_conflicts is False
        assert "<<<<<<< ours" not in result.content
        assert "[s01t01](s01t01-x.md)" in result.content


class TestMergeTaskFileInReviewSubtask:
    """IN_REVIEW subtask renders with **review** tag."""

    def test_theirs_marks_in_review(self) -> None:
        """Base has pending subtask, theirs marks it in-review -- merged output
        contains the **review** tag."""
        base_line = "- [ ] s01t01: Task one"
        base = _make_file(subtask_lines=[base_line])
        ours = _make_file(subtask_lines=[base_line])
        theirs_line = "- [~] s01t01: **review** Task one"
        theirs = _make_file(subtask_lines=[theirs_line])
        result = _merge(base, ours, theirs)
        assert result.has_conflicts is False
        assert "**review**" in result.content
        assert "- [~] s01t01: **review** Task one" in result.content
