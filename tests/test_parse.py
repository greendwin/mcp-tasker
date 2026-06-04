from pathlib import Path

import pytest

from tasker.base_types import Task, TaskStatus
from tasker.exceptions import TaskValidateError
from tasker.parse import (
    ParsedRef,
    ParsedSubtask,
    find_common_ancestor,
    make_child_ref,
    normalize_task_id,
    parse_task,
    parse_task_file,
    parse_task_ref,
)
from tasker.render import append_task_filename, render_task
from tasker.utils import write_text

_DIR = Path("/tmp/tasks")


def _write_task(
    name: str,
    title: str,
    description: str | None = None,
    status: TaskStatus = TaskStatus.PENDING,
) -> Path:
    stem = name.removesuffix(".md")
    task_id, slug = stem.split("-", 1)
    task = Task(
        id=task_id,
        slug=slug,
        title=title,
        description=description,
        status=status,
        subtasks=[],
    )

    task_path = append_task_filename(_DIR, task.ref, task.extended)
    write_text(task_path, render_task(task))

    return task_path


# ---------------------------------------------------------------------------
# parse_task_file — basic parsing
# ---------------------------------------------------------------------------


def test_parse_title() -> None:
    task = parse_task_file(_write_task("s01-my-task.md", "My task")).task
    assert task.title == "My task"


def test_parse_id_and_slug() -> None:
    task = parse_task_file(_write_task("s01-my-task.md", "My task")).task
    assert task.id == "s01"
    assert task.slug == "my-task"


def test_parse_status_pending() -> None:
    task = parse_task_file(_write_task("s01-my-task.md", "My task")).task
    assert task.status == TaskStatus.PENDING


def test_parse_status_in_progress() -> None:
    task = parse_task_file(
        _write_task("s01-my-task.md", "My task", status=TaskStatus.IN_PROGRESS)
    ).task
    assert task.status == TaskStatus.IN_PROGRESS


def test_parse_no_description() -> None:
    task = parse_task_file(_write_task("s01-my-task.md", "My task")).task
    assert task.description is None


def test_parse_description() -> None:
    task = parse_task_file(
        _write_task("s01-my-task.md", "My task", description="Some details")
    ).task
    assert task.description == "Some details"


def test_parse_multiline_description() -> None:
    task = parse_task_file(
        _write_task("s01-my-task.md", "My task", description="Line one\nLine two")
    ).task
    assert task.description == "Line one\nLine two"


def test_parse_simple_file_is_basic() -> None:
    task = parse_task_file(_write_task("s01-my-task.md", "My task")).task
    assert isinstance(task, Task)
    assert not task.extended


def test_parse_detailed_dir() -> None:
    task = Task(
        id="s01",
        slug="my-task",
        extended=True,
        title="My task",
    )
    task_path = append_task_filename(_DIR, task.ref, task.extended)
    write_text(task_path, render_task(task))

    parsed = parse_task_file(_DIR / "s01-my-task").task
    assert isinstance(parsed, Task)
    assert parsed.extended
    assert parsed.id == "s01"
    assert parsed.slug == "my-task"


def test_parse_returns_file_task() -> None:
    task = parse_task_file(_write_task("s01-my-task.md", "My task")).task
    assert isinstance(task, Task)


def test_parse_invalid_filename_raises() -> None:
    bad = _DIR / "bad-name.md"
    write_text(bad, "Title\n=====\n\n## Props\n\nStatus: pending\n")
    with pytest.raises(TaskValidateError):
        parse_task_file(bad)


# ---------------------------------------------------------------------------
# front-matter format tests
# ---------------------------------------------------------------------------


def test_file_has_front_matter_delimiters() -> None:
    path = _write_task("s01-my-task.md", "My task")
    content = path.read_text()
    assert content.startswith("---\n")
    assert "---\n" in content[4:]  # closing delimiter


def test_file_front_matter_has_id() -> None:
    path = _write_task("s01-my-task.md", "My task")
    content = path.read_text()
    assert "id: s01" in content


def test_file_front_matter_has_status() -> None:
    path = _write_task("s01-my-task.md", "My task")
    content = path.read_text()
    assert "status: pending" in content


def test_file_has_no_props_section() -> None:
    path = _write_task("s01-my-task.md", "My task")
    content = path.read_text()
    assert "## Props" not in content


def test_file_title_uses_atx_heading() -> None:
    path = _write_task("s01-my-task.md", "My task")
    content = path.read_text()
    assert "# My task" in content


def test_file_title_has_no_underline() -> None:
    path = _write_task("s01-my-task.md", "My task")
    content = path.read_text()
    assert "=======" not in content


def test_parse_raises_on_non_heading_title() -> None:
    bad = _DIR / "s01-my-task.md"
    write_text(bad, "---\nid: s01\nstatus: pending\n---\n\nMy task\n=======\n")
    with pytest.raises(TaskValidateError):
        parse_task_file(bad)


def test_parse_raises_on_missing_front_matter() -> None:
    bad = _DIR / "s01-my-task.md"
    write_text(bad, "My task\n=======\n\nStatus: pending\n")
    with pytest.raises(TaskValidateError):
        parse_task_file(bad)


def test_parse_raises_on_unclosed_front_matter() -> None:
    bad = _DIR / "s01-my-task.md"
    write_text(bad, "---\nid: s01\nstatus: pending\n")
    with pytest.raises(TaskValidateError):
        parse_task_file(bad)


# ---------------------------------------------------------------------------
# task_ref context on parse errors
# ---------------------------------------------------------------------------


def test_parse_error_has_task_ref() -> None:
    bad = _DIR / "s01-my-task.md"
    write_text(bad, "---\nid: s01\nstatus: pending\n---\n\nMy task\n=======\n")
    with pytest.raises(TaskValidateError) as exc_info:
        parse_task_file(bad)
    assert exc_info.value.task_ref is not None


def test_parse_error_task_ref_contains_filename() -> None:
    bad = _DIR / "s01-my-task.md"
    write_text(bad, "---\nid: s01\nstatus: pending\n---\n\nMy task\n=======\n")
    with pytest.raises(TaskValidateError) as exc_info:
        parse_task_file(bad)
    assert "s01-my-task" in (exc_info.value.task_ref or "")


def test_parse_invalid_filename_error_has_task_ref() -> None:
    bad = _DIR / "bad-name.md"
    write_text(bad, "")
    with pytest.raises(TaskValidateError) as exc_info:
        parse_task_file(bad)
    assert exc_info.value.task_ref is not None


# ---------------------------------------------------------------------------
# cancelled subtask strikethrough parsing
# ---------------------------------------------------------------------------


def _make_task_with_subtask_line(subtask_line: str) -> tuple[Task, list[ParsedSubtask]]:
    content = (
        "---\nid: s01\nstatus: pending\n---\n\n"
        "# My task\n\n## Subtasks\n\n" + subtask_line + "\n"
    )
    return parse_task(content, task_id="s01", slug="my-task", extended=False)


def test_parse_cancelled_subtask_new_format() -> None:
    _, subtasks = _make_task_with_subtask_line("- [x] ~~s01t01: My subtask~~")
    assert subtasks[0].status == TaskStatus.CANCELLED
    assert subtasks[0].title == "My subtask"


def test_parse_cancelled_subtask_legacy_format() -> None:
    _, subtasks = _make_task_with_subtask_line("- [x] s01t01: ~~My subtask~~")
    assert subtasks[0].status == TaskStatus.CANCELLED
    assert subtasks[0].title == "My subtask"


def test_parse_non_cancelled_subtask_no_strikethrough() -> None:
    _, subtasks = _make_task_with_subtask_line("- [ ] s01t01: My subtask")
    assert subtasks[0].status == TaskStatus.PENDING
    assert subtasks[0].title == "My subtask"


# ---------------------------------------------------------------------------
# managed section validation
# ---------------------------------------------------------------------------


def test_parse_raises_on_unknown_front_matter_field() -> None:
    bad = _DIR / "s01-my-task.md"
    write_text(bad, "---\nid: s01\nstatus: pending\npriority: high\n---\n\n# My task\n")
    with pytest.raises(TaskValidateError, match="priority"):
        parse_task_file(bad)


def test_parse_raises_on_invalid_subtask_line() -> None:
    content = (
        "---\nid: s01\nstatus: pending\n---\n\n"
        "# My task\n\n## Subtasks\n\n"
        "- [ ] s01t01: Valid subtask\n"
        "Some random text\n"
    )
    with pytest.raises(TaskValidateError, match="Invalid subtask line"):
        parse_task(content, task_id="s01", slug="my-task", extended=False)


def test_parse_allows_blank_lines_in_subtasks() -> None:
    content = (
        "---\nid: s01\nstatus: pending\n---\n\n"
        "# My task\n\n## Subtasks\n\n"
        "- [ ] s01t01: First\n"
        "\n"
        "- [ ] s01t02: Second\n"
    )
    _, subtasks = parse_task(content, task_id="s01", slug="my-task", extended=False)
    assert len(subtasks) == 2


# ---------------------------------------------------------------------------
# extra sections (non-managed)
# ---------------------------------------------------------------------------


def test_parse_preserves_depends_section() -> None:
    content = (
        "---\nid: s01\nstatus: pending\n---\n\n"
        "# My task\n\n"
        "## Depends\n\n"
        "- s02 - needs API design\n"
    )
    task, _ = parse_task(content, task_id="s01", slug="my-task", extended=False)
    assert task.extra_sections is not None
    assert "## Depends" in task.extra_sections
    assert "s02 - needs API design" in task.extra_sections


def test_parse_preserves_custom_section() -> None:
    content = (
        "---\nid: s01\nstatus: pending\n---\n\n"
        "# My task\n\nDescription text.\n\n"
        "## Notes\n\nSome notes here.\n"
    )
    task, _ = parse_task(content, task_id="s01", slug="my-task", extended=False)
    assert task.description == "Description text."
    assert task.extra_sections is not None
    assert "## Notes" in task.extra_sections
    assert "Some notes here." in task.extra_sections


def test_parse_preserves_section_after_subtasks() -> None:
    content = (
        "---\nid: s01\nstatus: pending\n---\n\n"
        "# My task\n\n"
        "## Subtasks\n\n"
        "- [ ] s01t01: First\n\n"
        "## Notes\n\nPost-subtask notes.\n"
    )
    task, subtasks = parse_task(content, task_id="s01", slug="my-task", extended=False)
    assert len(subtasks) == 1
    assert task.extra_sections is not None
    assert "Post-subtask notes." in task.extra_sections


def test_parse_preserves_multiple_extra_sections() -> None:
    content = (
        "---\nid: s01\nstatus: pending\n---\n\n"
        "# My task\n\n"
        "## Depends\n\n- s02\n\n"
        "## Notes\n\nSome notes.\n"
    )
    task, _ = parse_task(content, task_id="s01", slug="my-task", extended=False)
    assert task.extra_sections is not None
    assert "## Depends" in task.extra_sections
    assert "## Notes" in task.extra_sections


def test_extra_sections_roundtrip() -> None:
    content = (
        "---\nid: s01\nstatus: pending\n---\n\n"
        "# My task\n\nDescription.\n\n"
        "## Depends\n\n- s02 - needs API design\n\n"
        "## Subtasks\n\n"
        "- [ ] s01t01: First\n"
    )
    task, subtasks = parse_task(content, task_id="s01", slug="my-task", extended=False)
    task.subtasks = [
        Task(id=s.id, slug=s.slug, title=s.title, status=s.status) for s in subtasks
    ]

    rendered = render_task(task)
    assert "## Depends" in rendered
    assert "s02 - needs API design" in rendered
    assert "## Subtasks" in rendered
    assert "s01t01" in rendered
    assert "Description." in rendered


def test_no_extra_sections_when_absent() -> None:
    content = "---\nid: s01\nstatus: pending\n---\n\n" "# My task\n\nDescription.\n"
    task, _ = parse_task(content, task_id="s01", slug="my-task", extended=False)
    assert task.extra_sections is None


# ---------------------------------------------------------------------------
# slug normalization
# ---------------------------------------------------------------------------


def test_normalize_slug_from_filename_uppercase() -> None:
    path = _DIR / "s01-My-Task.md"
    write_text(path, "---\nid: s01\nstatus: pending\n---\n\n# My task\n")
    task = parse_task_file(path).task
    assert task.slug == "my-task"


def test_normalize_slug_from_filename_underscores() -> None:
    path = _DIR / "s01-my_task_name.md"
    write_text(path, "---\nid: s01\nstatus: pending\n---\n\n# My task\n")
    task = parse_task_file(path).task
    assert task.slug == "my-task-name"


def test_normalize_slug_from_filename_special_chars() -> None:
    path = _DIR / "s01-my...task!!name.md"
    write_text(path, "---\nid: s01\nstatus: pending\n---\n\n# My task\n")
    task = parse_task_file(path).task
    assert task.slug == "my-task-name"


def test_normalize_slug_from_frontmatter() -> None:
    path = _DIR / "s01-my-task.md"
    write_text(
        path,
        "---\nid: s01\nslug: My_Task_Name\nstatus: pending\n---\n\n# My task\n",
    )
    task = parse_task_file(path).task
    assert task.slug == "my-task-name"


def test_normalize_slug_preserves_valid_slug() -> None:
    path = _DIR / "s01-my-task.md"
    write_text(path, "---\nid: s01\nstatus: pending\n---\n\n# My task\n")
    task = parse_task_file(path).task
    assert task.slug == "my-task"


def test_normalize_slug_from_link_subtask() -> None:
    content = (
        "---\nid: s01\nstatus: pending\n---\n\n"
        "# My task\n\n## Subtasks\n\n"
        "- [ ] [s01t01](s01t01-My_Subtask.md): My subtask\n"
    )
    _, subtasks = parse_task(content, task_id="s01", slug="my-task", extended=False)
    assert subtasks[0].slug == "my-subtask"


# ---------------------------------------------------------------------------
# parse_task_ref — basic cases
# ---------------------------------------------------------------------------


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
# normalize_task_id
# ---------------------------------------------------------------------------


def test_normalize_task_id_pads_subtask() -> None:
    assert normalize_task_id("s1t5") == "s01t05"


def test_normalize_task_id_keeps_canonical_paste() -> None:
    assert normalize_task_id("s05t0302") == "s05t0302"


def test_normalize_task_id_pads_root() -> None:
    assert normalize_task_id("s1") == "s01"


def test_normalize_task_id_two_digit_subtask() -> None:
    assert normalize_task_id("s1t12") == "s01t12"


def test_normalize_task_id_strips_slug() -> None:
    assert normalize_task_id("s01-foo") == "s01"


def test_normalize_task_id_passthrough_on_non_match() -> None:
    assert normalize_task_id("q") == "q"


def test_normalize_task_id_raises_on_ambiguous_digits() -> None:
    with pytest.raises(TaskValidateError, match="Ambiguous digits"):
        normalize_task_id("s1t123")


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
