from pathlib import Path

from jinja2 import Environment, PackageLoader

from .base_types import EXTENDED_TASK_FILENAME, Task, TaskStatus

_CHECKBOX = {
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
    return _CHECKBOX[status]


_jinja.filters["checkbox"] = _to_checkbox


def render_task(task: Task) -> str:
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
