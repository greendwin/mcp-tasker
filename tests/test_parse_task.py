from pathlib import Path

import pytest

from tasker.base_types import Task, TaskStatus
from tasker.exceptions import TaskValidateError
from tasker.parse import ParsedSubtask, parse_task, parse_task_file
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


# --- front-matter format tests ---


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


# --- task_ref context on parse errors ---


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


# --- cancelled subtask strikethrough parsing ---


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


# --- managed section validation ---


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


# --- extra sections (non-managed) ---


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


# --- slug normalization ---


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
