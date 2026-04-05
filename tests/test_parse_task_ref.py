import pytest

from tasker.exceptions import TaskValidateError
from tasker.parse import ParsedRef, find_common_ancestor, make_child_ref, parse_task_ref


def test_root_story_id_only() -> None:
    result = parse_task_ref("s01")
    assert result == ParsedRef(
        task_ref="s01", task_id="s01", parent_id="s01", root_id="s01", slug=None
    )


def test_root_story_with_slug() -> None:
    result = parse_task_ref("s01-my-story")
    assert result == ParsedRef(
        task_ref="s01-my-story",
        task_id="s01",
        parent_id="s01",
        root_id="s01",
        slug="my-story",
    )


def test_direct_subtask_id_only() -> None:
    result = parse_task_ref("s01t01")
    assert result == ParsedRef(
        task_ref="s01t01", task_id="s01t01", parent_id="s01", root_id="s01", slug=None
    )


def test_direct_subtask_with_slug() -> None:
    result = parse_task_ref("s01t01-define-task-forms")
    assert result == ParsedRef(
        task_ref="s01t01-define-task-forms",
        task_id="s01t01",
        parent_id="s01",
        root_id="s01",
        slug="define-task-forms",
    )


def test_nested_subtask() -> None:
    result = parse_task_ref("s01t0102")
    assert result == ParsedRef(
        task_ref="s01t0102",
        task_id="s01t0102",
        parent_id="s01t01",
        root_id="s01",
        slug=None,
    )


def test_deeply_nested_subtask() -> None:
    result = parse_task_ref("s01t010203")
    assert result == ParsedRef(
        task_ref="s01t010203",
        task_id="s01t010203",
        parent_id="s01t0102",
        root_id="s01",
        slug=None,
    )


def test_multi_digit_story_number() -> None:
    result = parse_task_ref("s123t01")
    assert result == ParsedRef(
        task_ref="s123t01",
        task_id="s123t01",
        parent_id="s123",
        root_id="s123",
        slug=None,
    )


def test_invalid_ref_raises() -> None:
    with pytest.raises(TaskValidateError, match="Invalid task ref"):
        parse_task_ref("invalid")


def test_empty_ref_raises() -> None:
    with pytest.raises(TaskValidateError, match="Invalid task ref"):
        parse_task_ref("")


def test_partial_subtask_id_raises() -> None:
    # "t" alone without a digit group is not valid
    with pytest.raises(TaskValidateError, match="Invalid task ref"):
        parse_task_ref("t01")


# ---------------------------------------------------------------------------
# make_child_ref
# ---------------------------------------------------------------------------


def test_make_child_ref_from_root() -> None:
    assert make_child_ref("s01", "01") == "s01t01"


def test_make_child_ref_from_subtask() -> None:
    assert make_child_ref("s01t02", "01") == "s01t0201"


def test_make_child_ref_from_nested_subtask() -> None:
    assert make_child_ref("s01t0203", "04") == "s01t020304"


def test_make_child_ref_deep_digits() -> None:
    assert make_child_ref("s01", "0102") == "s01t0102"


def test_make_child_ref_empty_digits() -> None:
    # Used by get_next_subtask_id to get the prefix
    assert make_child_ref("s01", "") == "s01t"
    assert make_child_ref("s01t02", "") == "s01t02"


# ---------------------------------------------------------------------------
# find_common_ancestor
# ---------------------------------------------------------------------------


def test_common_ancestor_empty_is_denied() -> None:
    with pytest.raises(AssertionError):
        _ = find_common_ancestor([])


def test_common_ancestor_single() -> None:
    assert find_common_ancestor(["s01t01"]) == "s01t01"


def test_common_ancestor_same() -> None:
    assert find_common_ancestor(["s01t01", "s01t01"]) == "s01t01"


def test_common_ancestor_siblings() -> None:
    assert find_common_ancestor(["s01t01", "s01t02"]) == "s01"


def test_common_ancestor_nested_siblings() -> None:
    assert find_common_ancestor(["s01t0201", "s01t0202"]) == "s01t02"


def test_common_ancestor_different_depth() -> None:
    assert find_common_ancestor(["s01t01", "s01t0102"]) == "s01t01"


def test_common_ancestor_root_and_subtask() -> None:
    assert find_common_ancestor(["s01", "s01t01"]) == "s01"


def test_common_ancestor_different_stories() -> None:
    assert find_common_ancestor(["s01t01", "s02t01"]) == "s02t01"


def test_common_ancestor_three_tasks() -> None:
    assert find_common_ancestor(["s01t0101", "s01t0102", "s01t0103"]) == "s01t01"


def test_common_ancestor_three_tasks_different_parents() -> None:
    assert find_common_ancestor(["s01t0101", "s01t0201", "s01t0301"]) == "s01"


def test_common_ancestor_root_tasks() -> None:
    assert find_common_ancestor(["s01", "s01"]) == "s01"
