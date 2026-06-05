from __future__ import annotations

from typing import Any

import pytest

from tasker.base_types import Task, TaskStatus
from tasker.merge import Merged, merge_scalar_fields


def _task(**overrides: Any) -> Task:
    defaults: dict[str, Any] = {
        "id": "s01t01",
        "status": TaskStatus.PENDING,
        "title": "Default title",
        "slug": "default-slug",
        "description": "Default description",
        "extra_sections": None,
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
        assert result.extra_sections == Merged(None)


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
        assert result.extra_sections == Merged(None)


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
            ("extra_sections", "Base extra", "Ours extra", "Theirs extra"),
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
            ("extra_sections", None, "New extra"),
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
            ("extra_sections", None, "New extra"),
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
