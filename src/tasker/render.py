from pathlib import Path

from jinja2 import Environment, PackageLoader

from .base_types import EXTENDED_TASK_FILENAME, Task, TaskStatus, build_task_ref
from .parse import ParsedSubtask

STATUS_CHECKBOX: dict[TaskStatus, str] = {
    TaskStatus.PENDING: " ",
    TaskStatus.IN_PROGRESS: "~",
    TaskStatus.IN_REVIEW: "~",
    TaskStatus.DONE: "x",
    TaskStatus.CANCELLED: "x",
}

_jinja = Environment(
    loader=PackageLoader("tasker", "templates"),
    keep_trailing_newline=True,
    trim_blocks=True,
    lstrip_blocks=True,
)


def _to_checkbox(status: TaskStatus) -> str:
    return STATUS_CHECKBOX[status]


def render_subtask_line(sub: ParsedSubtask) -> str:
    checkbox = STATUS_CHECKBOX[sub.status]
    review_tag = "**review** " if sub.status == TaskStatus.IN_REVIEW else ""

    if sub.slug is not None:
        ref = build_task_ref(sub.id, sub.slug)
        link = f"{ref}/" if sub.extended else f"{ref}.md"
        if sub.status == TaskStatus.CANCELLED:
            return f"- [{checkbox}] ~~[{sub.id}]({link}): {sub.title}~~"
        return f"- [{checkbox}] [{sub.id}]({link}): {review_tag}{sub.title}"

    if sub.status == TaskStatus.CANCELLED:
        return f"- [{checkbox}] ~~{sub.id}: {sub.title}~~"
    return f"- [{checkbox}] {sub.id}: {review_tag}{sub.title}"


def render_task(task: Task) -> str:
    _jinja.filters["checkbox"] = _to_checkbox
    _jinja.filters["subtask_line"] = render_subtask_line
    return _jinja.get_template("task.md.j2").render(
        id=task.id,
        slug=task.slug,
        title=task.title,
        description=task.description,
        extra_sections=task.extra_sections,
        status=task.status.value,
        subtasks=task.subtasks,
    )


def append_task_filename(parent_dir: Path, task_ref: str, extended: bool) -> Path:
    if not extended:
        return parent_dir / f"{task_ref}.md"
    return parent_dir / task_ref / EXTENDED_TASK_FILENAME
