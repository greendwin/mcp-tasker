import pytest
from pydantic import ValidationError

from tasker.base_types import Task


def test_unknown_field_raises() -> None:
    with pytest.raises(ValidationError, match="extra_sections") as exc_info:
        Task.model_validate({"id": "s1t1", "title": "x", "extra_sections": "x"})

    errors = exc_info.value.errors()
    assert errors[0]["type"] == "extra_forbidden"
    assert errors[0]["loc"] == ("extra_sections",)


def test_known_fields_construct() -> None:
    task = Task(id="s1t1", title="x")
    assert task.id == "s1t1"
    assert task.title == "x"
