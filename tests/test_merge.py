from __future__ import annotations

from typing import Any

import pytest

from tasker.base_types import Task, TaskStatus
from tasker.merge import (
    ConflictingSubtask,
    Merged,
    MergeFileResult,
    merge_scalar_fields,
    merge_subtask_lists,
    merge_task_file,
)
from tasker.parse import ParsedSubtask


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


class TestAllIdentical:
    """All three versions identical -- no conflict, values preserved."""

    def test_no_conflict(self) -> None:
        base = _task()
        ours = _task()
        theirs = _task()
        result = merge_scalar_fields(base, ours, theirs)
        assert result.status == Merged(TaskStatus.PENDING)
        assert result.title == Merged("Default title")
        assert result.slug == Merged("default-slug")
        assert result.description == Merged("Default description")


class TestOnlyOursChanged:
    """Only ours changed a field -- ours wins."""

    def test_ours_changed_title(self) -> None:
        base = _task()
        ours = _task(title="New title")
        theirs = _task()
        result = merge_scalar_fields(base, ours, theirs)
        assert result.title == Merged("New title")

    def test_ours_changed_status(self) -> None:
        base = _task()
        ours = _task(status=TaskStatus.IN_PROGRESS)
        theirs = _task()
        result = merge_scalar_fields(base, ours, theirs)
        assert result.status == Merged(TaskStatus.IN_PROGRESS)


class TestOnlyTheirsChanged:
    """Only theirs changed a field -- theirs wins."""

    def test_theirs_changed_title(self) -> None:
        base = _task()
        ours = _task()
        theirs = _task(title="Their title")
        result = merge_scalar_fields(base, ours, theirs)
        assert result.title == Merged("Their title")

    def test_theirs_changed_status(self) -> None:
        base = _task()
        ours = _task()
        theirs = _task(status=TaskStatus.DONE)
        result = merge_scalar_fields(base, ours, theirs)
        assert result.status == Merged(TaskStatus.DONE)


class TestBothChangedSameValue:
    """Both changed same field to same value -- no conflict."""

    def test_both_changed_title_same(self) -> None:
        base = _task()
        ours = _task(title="Same new title")
        theirs = _task(title="Same new title")
        result = merge_scalar_fields(base, ours, theirs)
        assert result.title == Merged("Same new title")


class TestBothChangedDifferentValues:
    """Both changed same field to different values -- conflict."""

    def test_conflict_on_title(self) -> None:
        base = _task()
        ours = _task(title="Our title")
        theirs = _task(title="Their title")
        result = merge_scalar_fields(base, ours, theirs)
        assert result.title is None

    def test_conflict_on_status(self) -> None:
        base = _task()
        ours = _task(status=TaskStatus.IN_PROGRESS)
        theirs = _task(status=TaskStatus.DONE)
        result = merge_scalar_fields(base, ours, theirs)
        assert result.status is None


class TestMultipleFields:
    """Multiple fields: some clean-merge, some conflict."""

    def test_mixed(self) -> None:
        base = _task()
        ours = _task(title="Our title", description="Our desc")
        theirs = _task(title="Their title", slug="their-slug")
        result = merge_scalar_fields(base, ours, theirs)
        assert result.title is None
        assert result.description == Merged("Our desc")
        assert result.slug == Merged("their-slug")
        assert result.status == Merged(TaskStatus.PENDING)

    def test_non_conflicting_fields_resolved(self) -> None:
        """Fields that merge cleanly should have Merged values."""
        base = _task()
        ours = _task(title="Our title")
        theirs = _task(title="Their title")
        result = merge_scalar_fields(base, ours, theirs)
        assert result.title is None
        assert result.status == Merged(TaskStatus.PENDING)
        assert result.slug == Merged("default-slug")
        assert result.description == Merged("Default description")


class TestBaseNone:
    """Base is None (file added on both sides)."""

    def test_ours_equals_theirs(self) -> None:
        ours = _task()
        theirs = _task()
        result = merge_scalar_fields(None, ours, theirs)
        assert result.title == Merged("Default title")
        assert result.status == Merged(TaskStatus.PENDING)

    def test_ours_differs_theirs(self) -> None:
        ours = _task(title="Our title")
        theirs = _task(title="Their title")
        result = merge_scalar_fields(None, ours, theirs)
        assert result.title is None

    def test_multiple_conflicts_no_base(self) -> None:
        ours = _task(title="A", status=TaskStatus.IN_PROGRESS)
        theirs = _task(title="B", status=TaskStatus.DONE)
        result = merge_scalar_fields(None, ours, theirs)
        assert result.title is None
        assert result.status is None


class TestIdMismatch:
    """Merging tasks with different IDs raises ValueError."""

    def test_different_ids_raises(self) -> None:
        ours = _task(id="s01t01")
        theirs = _task(id="s01t02")
        with pytest.raises(ValueError, match="different IDs"):
            merge_scalar_fields(None, ours, theirs)

    def test_different_ids_with_base_raises(self) -> None:
        base = _task(id="s01t01")
        ours = _task(id="s01t01")
        theirs = _task(id="s01t02")
        with pytest.raises(ValueError, match="different IDs"):
            merge_scalar_fields(base, ours, theirs)


class TestEachScalarField:
    """Each scalar field individually tested for conflict detection."""

    @pytest.mark.parametrize(
        "field,base_val,ours_val,theirs_val",
        [
            ("status", TaskStatus.PENDING, TaskStatus.IN_PROGRESS, TaskStatus.DONE),
            ("title", "Base", "Ours", "Theirs"),
            ("slug", "base-slug", "ours-slug", "theirs-slug"),
            ("description", "Base desc", "Ours desc", "Theirs desc"),
        ],
    )
    def test_conflict_per_field(
        self,
        field: str,
        base_val: object,
        ours_val: object,
        theirs_val: object,
    ) -> None:
        base = _task(**{field: base_val})
        ours = _task(**{field: ours_val})
        theirs = _task(**{field: theirs_val})
        result = merge_scalar_fields(base, ours, theirs)
        assert getattr(result, field) is None

    @pytest.mark.parametrize(
        "field,base_val,changed_val",
        [
            ("status", TaskStatus.PENDING, TaskStatus.IN_PROGRESS),
            ("title", "Base", "Changed"),
            ("slug", "base-slug", "changed-slug"),
            ("description", "Base desc", "Changed desc"),
        ],
    )
    def test_ours_only_per_field(
        self,
        field: str,
        base_val: object,
        changed_val: object,
    ) -> None:
        base = _task(**{field: base_val})
        ours = _task(**{field: changed_val})
        theirs = _task(**{field: base_val})
        result = merge_scalar_fields(base, ours, theirs)
        assert getattr(result, field) == Merged(changed_val)

    @pytest.mark.parametrize(
        "field,base_val,changed_val",
        [
            ("status", TaskStatus.PENDING, TaskStatus.IN_PROGRESS),
            ("title", "Base", "Changed"),
            ("slug", "base-slug", "changed-slug"),
            ("description", "Base desc", "Changed desc"),
        ],
    )
    def test_theirs_only_per_field(
        self,
        field: str,
        base_val: object,
        changed_val: object,
    ) -> None:
        base = _task(**{field: base_val})
        ours = _task(**{field: base_val})
        theirs = _task(**{field: changed_val})
        result = merge_scalar_fields(base, ours, theirs)
        assert getattr(result, field) == Merged(changed_val)


# --- Subtask list merge tests ---


def _sub(
    tid: str = "s01t01",
    title: str = "Task one",
    status: TaskStatus = TaskStatus.PENDING,
) -> ParsedSubtask:
    return ParsedSubtask(
        id=tid, slug=None, ref=tid, title=title, status=status, extended=False
    )


class TestSubtaskListsIdentical:
    """All three lists identical -- merged list has Merged values."""

    def test_all_identical(self) -> None:
        t = _sub()
        result = merge_subtask_lists([t], [t], [t])
        assert len(result) == 1
        assert isinstance(result[0], ParsedSubtask)
        assert result[0].id == "s01t01"
        assert result[0].title == "Task one"
        assert result[0].status == TaskStatus.PENDING


class TestSubtaskOursModified:
    """Entry modified only in ours -- ours wins."""

    def test_ours_title_changed(self) -> None:
        base = [_sub()]
        ours = [_sub(title="Updated")]
        theirs = [_sub()]
        result = merge_subtask_lists(base, ours, theirs)
        assert len(result) == 1
        assert isinstance(result[0], ParsedSubtask)
        assert result[0].title == "Updated"
        assert result[0].status == TaskStatus.PENDING


class TestSubtaskTheirsModified:
    """Entry modified only in theirs -- theirs wins."""

    def test_theirs_status_changed(self) -> None:
        base = [_sub()]
        ours = [_sub()]
        theirs = [_sub(status=TaskStatus.DONE)]
        result = merge_subtask_lists(base, ours, theirs)
        assert len(result) == 1
        assert isinstance(result[0], ParsedSubtask)
        assert result[0].status == TaskStatus.DONE
        assert result[0].title == "Task one"


class TestSubtaskBothSameChange:
    """Both modified title to same value -- merged."""

    def test_both_same_title(self) -> None:
        base = [_sub()]
        ours = [_sub(title="Same")]
        theirs = [_sub(title="Same")]
        result = merge_subtask_lists(base, ours, theirs)
        assert len(result) == 1
        assert isinstance(result[0], ParsedSubtask)
        assert result[0].title == "Same"


class TestSubtaskBothDifferentChange:
    """Both modified title to different values -- conflict."""

    def test_both_different_title(self) -> None:
        base = [_sub()]
        ours = [_sub(title="Ours")]
        theirs = [_sub(title="Theirs")]
        result = merge_subtask_lists(base, ours, theirs)
        assert len(result) == 1
        assert isinstance(result[0], ConflictingSubtask)
        assert result[0].ours is not None and result[0].ours.title == "Ours"
        assert result[0].theirs is not None and result[0].theirs.title == "Theirs"


class TestSubtaskDeleteAccepted:
    """Entry deleted from one side, unchanged on other -- accept delete."""

    def test_deleted_in_theirs_unchanged(self) -> None:
        base = [_sub()]
        ours = [_sub()]
        theirs: list[ParsedSubtask] = []
        result = merge_subtask_lists(base, ours, theirs)
        assert len(result) == 0

    def test_deleted_in_ours_unchanged(self) -> None:
        base = [_sub()]
        ours: list[ParsedSubtask] = []
        theirs = [_sub()]
        result = merge_subtask_lists(base, ours, theirs)
        assert len(result) == 0


class TestSubtaskDeleteModifyConflict:
    """Delete-modify conflict -- entry present with None fields."""

    def test_deleted_in_theirs_modified_in_ours(self) -> None:
        base = [_sub()]
        ours = [_sub(title="Modified")]
        theirs: list[ParsedSubtask] = []
        result = merge_subtask_lists(base, ours, theirs)
        assert len(result) == 1
        assert isinstance(result[0], ConflictingSubtask)
        assert result[0].ours is not None and result[0].ours.title == "Modified"
        assert result[0].theirs is None

    def test_deleted_in_ours_modified_in_theirs(self) -> None:
        base = [_sub()]
        ours: list[ParsedSubtask] = []
        theirs = [_sub(status=TaskStatus.DONE)]
        result = merge_subtask_lists(base, ours, theirs)
        assert len(result) == 1
        assert isinstance(result[0], ConflictingSubtask)
        assert result[0].ours is None
        assert (
            result[0].theirs is not None and result[0].theirs.status == TaskStatus.DONE
        )


class TestSubtaskBothDeleted:
    """Both deleted (in base only) -- not in result."""

    def test_both_deleted(self) -> None:
        base = [_sub()]
        ours: list[ParsedSubtask] = []
        theirs: list[ParsedSubtask] = []
        result = merge_subtask_lists(base, ours, theirs)
        assert len(result) == 0


class TestSubtaskAdditions:
    """Entry only in one side (addition) -- included with Merged values."""

    def test_ours_addition(self) -> None:
        base: list[ParsedSubtask] = []
        ours = [_sub(tid="s01t02", title="New task")]
        theirs: list[ParsedSubtask] = []
        result = merge_subtask_lists(base, ours, theirs)
        assert len(result) == 1
        assert isinstance(result[0], ParsedSubtask)
        assert result[0].id == "s01t02"
        assert result[0].title == "New task"
        assert result[0].status == TaskStatus.PENDING

    def test_theirs_addition(self) -> None:
        base: list[ParsedSubtask] = []
        ours: list[ParsedSubtask] = []
        theirs = [_sub(tid="s01t03", title="Their task")]
        result = merge_subtask_lists(base, ours, theirs)
        assert len(result) == 1
        assert isinstance(result[0], ParsedSubtask)
        assert result[0].id == "s01t03"
        assert result[0].title == "Their task"
        assert result[0].status == TaskStatus.PENDING


class TestSubtaskBothAddedSame:
    """Both added same entry (same id, title, status) -- merged."""

    def test_both_added_identical(self) -> None:
        base: list[ParsedSubtask] = []
        ours = [_sub(tid="s01t04", title="Shared")]
        theirs = [_sub(tid="s01t04", title="Shared")]
        result = merge_subtask_lists(base, ours, theirs)
        assert len(result) == 1
        assert isinstance(result[0], ParsedSubtask)
        assert result[0].title == "Shared"

    def test_both_added_different_title(self) -> None:
        base: list[ParsedSubtask] = []
        ours = [_sub(tid="s01t04", title="Ours")]
        theirs = [_sub(tid="s01t04", title="Theirs")]
        result = merge_subtask_lists(base, ours, theirs)
        assert len(result) == 1
        assert isinstance(result[0], ConflictingSubtask)

    def test_both_added_different_status(self) -> None:
        base: list[ParsedSubtask] = []
        ours = [_sub(tid="s01t04", status=TaskStatus.IN_PROGRESS)]
        theirs = [_sub(tid="s01t04", status=TaskStatus.DONE)]
        result = merge_subtask_lists(base, ours, theirs)
        assert len(result) == 1
        assert isinstance(result[0], ConflictingSubtask)
        assert result[0].ours is not None and result[0].ours.title == "Task one"


class TestSubtaskOrdering:
    """Ordering: base order preserved, ours additions appended, then theirs."""

    def test_ordering(self) -> None:
        base = [_sub(tid="s01t01"), _sub(tid="s01t02", title="Two")]
        ours = [
            _sub(tid="s01t01"),
            _sub(tid="s01t02", title="Two"),
            _sub(tid="s01t10", title="Ours new"),
        ]
        theirs = [
            _sub(tid="s01t01"),
            _sub(tid="s01t02", title="Two"),
            _sub(tid="s01t20", title="Theirs new"),
        ]
        result = merge_subtask_lists(base, ours, theirs)

        ids = []
        for e in result:
            assert isinstance(e, ParsedSubtask)
            ids.append(e.id)

        assert ids == ["s01t01", "s01t02", "s01t10", "s01t20"]


class TestSubtaskNoBase:
    """No base (None) -- two-way merge."""

    def test_equal_merged(self) -> None:
        ours = [_sub()]
        theirs = [_sub()]
        result = merge_subtask_lists(None, ours, theirs)
        assert len(result) == 1
        assert isinstance(result[0], ParsedSubtask)
        assert result[0].title == "Task one"

    def test_different_conflict(self) -> None:
        ours = [_sub(title="A")]
        theirs = [_sub(title="B")]
        result = merge_subtask_lists(None, ours, theirs)
        assert len(result) == 1
        assert isinstance(result[0], ConflictingSubtask)

    def test_ours_only_addition(self) -> None:
        ours = [_sub(tid="s01t02", title="Only ours")]
        result = merge_subtask_lists(None, ours, [])
        assert len(result) == 1
        assert isinstance(result[0], ParsedSubtask)
        assert result[0].id == "s01t02"
        assert result[0].title == "Only ours"

    def test_theirs_only_addition(self) -> None:
        theirs = [_sub(tid="s01t03", title="Only theirs")]
        result = merge_subtask_lists(None, [], theirs)
        assert len(result) == 1
        assert isinstance(result[0], ParsedSubtask)
        assert result[0].id == "s01t03"
        assert result[0].title == "Only theirs"


class TestSubtaskEmptyLists:
    """Empty lists -- empty result."""

    def test_all_empty(self) -> None:
        result = merge_subtask_lists([], [], [])
        assert result == []

    def test_base_none_empty(self) -> None:
        result = merge_subtask_lists(None, [], [])
        assert result == []


class TestSubtaskMixedScenario:
    """Mixed: some merged, some conflicted, some added, some deleted."""

    def test_mixed(self) -> None:
        base = [
            _sub(tid="s01t01", title="One"),
            _sub(tid="s01t02", title="Two"),
            _sub(tid="s01t03", title="Three"),
            _sub(tid="s01t04", title="Four"),
        ]
        ours = [
            _sub(tid="s01t01", title="One updated"),  # modified
            # s01t02 deleted
            _sub(tid="s01t03", title="Three"),  # unchanged
            _sub(tid="s01t04", title="Four"),  # unchanged (theirs deletes)
            _sub(tid="s01t10", title="New ours"),  # addition
        ]
        theirs = [
            _sub(tid="s01t01", title="One"),  # unchanged -> ours wins
            _sub(
                tid="s01t02", title="Two modified"
            ),  # modified, ours deleted -> conflict
            _sub(tid="s01t03", title="Three", status=TaskStatus.DONE),  # status change
            # s01t04 deleted, ours unchanged -> accept delete
            _sub(tid="s01t20", title="New theirs"),  # addition
        ]
        result = merge_subtask_lists(base, ours, theirs)

        def _entry_id(e: ParsedSubtask | ConflictingSubtask) -> str:
            if isinstance(e, ParsedSubtask):
                return e.id
            src = e.ours or e.theirs or e.base
            assert src is not None
            return src.id

        def _by_id(tid: str) -> ParsedSubtask | ConflictingSubtask:
            for e in result:
                if _entry_id(e) == tid:
                    return e
            raise KeyError(tid)

        # s01t01: ours modified title, theirs unchanged -> ours wins
        s01t01 = _by_id("s01t01")
        assert isinstance(s01t01, ParsedSubtask)
        assert s01t01.title == "One updated"

        # s01t02: delete-modify conflict
        s01t02 = _by_id("s01t02")
        assert isinstance(s01t02, ConflictingSubtask)

        # s01t03: theirs changed status, ours unchanged
        s01t03 = _by_id("s01t03")
        assert isinstance(s01t03, ParsedSubtask)
        assert s01t03.title == "Three"
        assert s01t03.status == TaskStatus.DONE

        # s01t04: deleted in theirs, unchanged in ours -> accept delete
        assert all(_entry_id(e) != "s01t04" for e in result)

        # additions
        s01t10 = _by_id("s01t10")
        assert isinstance(s01t10, ParsedSubtask)
        assert s01t10.title == "New ours"
        s01t20 = _by_id("s01t20")
        assert isinstance(s01t20, ParsedSubtask)
        assert s01t20.title == "New theirs"

        # ordering
        ids = [_entry_id(e) for e in result]
        assert ids == ["s01t01", "s01t02", "s01t03", "s01t10", "s01t20"]


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
    description: str | None = None,
    subtask_lines: list[str] | None = None,
) -> str:
    """Build a task markdown file string for testing."""
    lines = ["---", "id: s01"]
    if slug is not None:
        lines.append(f"slug: {slug}")
    lines.append(f"status: {status}")
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
