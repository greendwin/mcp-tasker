from tasker.base_types import Task, TaskStatus
from tasker.mcp._model import TaskPreview
from tasker.mcp._render import (
    render_task_error,
    render_task_line,
    render_task_markdown,
    truncate_title,
)

# --- render_task_markdown ---


def test_render_markdown_root_has_no_parent_line() -> None:
    task = Task(id="s26", title="Root story", slug="root-story")
    result = render_task_markdown(task)
    assert result.startswith("# s26: Root story")
    assert "status: pending" in result
    assert "parent:" not in result


def test_render_markdown_subtask_has_parent_line() -> None:
    task = Task(id="s26t01", title="Child", slug="child")
    result = render_task_markdown(task)
    assert "parent: s26" in result


def test_render_markdown_includes_body_verbatim() -> None:
    task = Task(id="s26", title="Story", slug="story", description="Body text.")
    result = render_task_markdown(task)
    assert "Body text." in result


def test_render_markdown_omits_body_when_none() -> None:
    task = Task(id="s26", title="Story", slug="story")
    assert render_task_markdown(task) == "# s26: Story\nstatus: pending"


def test_render_markdown_lists_subtasks() -> None:
    child = Task(id="s26t01", title="Child", slug="child")
    task = Task(id="s26", title="Story", slug="story", subtasks=[child])
    result = render_task_markdown(task)
    assert "## Subtasks" in result
    assert "s26t01" in result.split("## Subtasks", 1)[1]


def test_render_markdown_omits_subtasks_section_when_empty() -> None:
    task = Task(id="s26", title="Story", slug="story")
    assert "## Subtasks" not in render_task_markdown(task)


# --- render_task_error ---


def test_render_task_error_format() -> None:
    assert render_task_error("s99", "not found") == "# s99: not found"


def test_render_task_error_collapses_newlines_in_message() -> None:
    result = render_task_error("s99", "first line\n\nsecond line")
    assert "\n" not in result
    assert result == "# s99: first line second line"


# --- truncate_title ---


def test_truncate_title_short_unchanged() -> None:
    title = "Short title"
    assert truncate_title(title) == title


def test_truncate_title_exact_60_unchanged() -> None:
    title = "a" * 60
    assert truncate_title(title) == title


def test_truncate_title_over_60_cuts_on_word_boundary() -> None:
    # 50 chars + space + 10 chars = 61 chars total
    title = "a" * 50 + " " + "b" * 10
    result = truncate_title(title)
    assert result.endswith("...")
    assert len(result) <= 60
    assert result == "a" * 50 + "..."


def test_truncate_title_single_long_word_hard_cut() -> None:
    title = "a" * 70
    result = truncate_title(title)
    assert result == "a" * 57 + "..."
    assert len(result) == 60


def test_truncate_title_custom_max_len() -> None:
    title = "hello world this is long"
    result = truncate_title(title, max_len=15)
    assert result.endswith("...")
    assert len(result) <= 15


def test_truncate_title_word_boundary_prefers_last_space() -> None:
    # "word1 word2 word3" where cutting at 15 means max_len-3=12
    title = "abcde fghij klmnop"
    result = truncate_title(title, max_len=15)
    # last space at or before position 12 is at index 11
    assert result == "abcde fghij..."


def test_truncate_title_space_at_exact_boundary() -> None:
    title = "a" * 57 + " bbb"  # 61 chars, space at position 57 = cut_at
    result = truncate_title(title)
    assert result == "a" * 57 + "..."
    assert len(result) == 60


# --- render_task_line ---


def test_render_task_line_basic() -> None:
    preview = TaskPreview(id="s01", title="My task", status=TaskStatus.PENDING)
    result = render_task_line(preview)
    assert result == ". s01  My task"


def test_render_task_line_with_body() -> None:
    preview = TaskPreview(
        id="s01", title="My task", status=TaskStatus.PENDING, has_body=True
    )
    result = render_task_line(preview)
    assert result == ". s01  My task (...)"


def test_render_task_line_in_progress() -> None:
    preview = TaskPreview(id="s02", title="Working", status=TaskStatus.IN_PROGRESS)
    result = render_task_line(preview)
    assert result == "~ s02  Working"


def test_render_task_line_truncation_and_body() -> None:
    long_title = "a" * 50 + " " + "b" * 10
    preview = TaskPreview(
        id="s01", title=long_title, status=TaskStatus.DONE, has_body=True
    )
    result = render_task_line(preview)
    assert "..." in result
    assert result.endswith("(...)")


def test_render_task_line_short_title_with_body_no_ellipsis() -> None:
    preview = TaskPreview(
        id="s01", title="Short", status=TaskStatus.PENDING, has_body=True
    )
    result = render_task_line(preview)
    assert result == ". s01  Short (...)"
    # No truncation ellipsis in the title part
    assert result.count("...") == 1


def test_render_task_line_reads_has_body_from_preview() -> None:
    preview = TaskPreview(
        id="s01", title="Auto body", status=TaskStatus.PENDING, has_body=True
    )
    result = render_task_line(preview)
    assert "(...)" in result


def test_render_task_line_long_title_no_body_no_marker() -> None:
    long_title = "a" * 70
    preview = TaskPreview(id="s01", title=long_title, status=TaskStatus.PENDING)
    result = render_task_line(preview)
    assert "..." in result
    assert "(...)" not in result


def test_render_task_line_varying_id_widths() -> None:
    p1 = TaskPreview(id="s1", title="Task", status=TaskStatus.PENDING)
    p2 = TaskPreview(id="s123t4567", title="Task", status=TaskStatus.PENDING)
    r1 = render_task_line(p1)
    r2 = render_task_line(p2)
    assert r1 == ". s1  Task"
    assert r2 == ". s123t4567  Task"
