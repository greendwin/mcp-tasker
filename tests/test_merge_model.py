from __future__ import annotations

from typing import Any

import pytest

from tasker.base_types import Task, TaskStatus
from tasker.merge import (
    ConflictingSubtask,
    Merged,
    merge_scalar_fields,
    merge_subtask_lists,
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
