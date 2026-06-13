from tasker.base_types import Task, TaskStatus
from tasker.parse import task_parent_id

from ._model import TaskPreview

TASK_BLOCK_SEPARATOR = "\n\n---\n\n"

_STATUS_SIGNS: dict[TaskStatus, str] = {
    TaskStatus.PENDING: ".",
    TaskStatus.IN_PROGRESS: "~",
    TaskStatus.IN_REVIEW: "?",
    TaskStatus.DONE: "x",
    TaskStatus.CANCELLED: "-",
}


def truncate_title(title: str, max_len: int = 60) -> str:
    # truncate on word boundary with '...' only when actually cut
    if len(title) <= max_len:
        return title

    cut_at = max_len - 3
    space_pos = title.rfind(" ", 0, cut_at + 1)
    if space_pos > 0:
        return title[:space_pos] + "..."
    return title[:cut_at] + "..."


def render_task_line(preview: TaskPreview) -> str:
    # one task line: '<sign> <id>  <truncated-title>[ (...)]'
    sign = _STATUS_SIGNS[preview.status]
    title = truncate_title(preview.title)
    line = f"{sign} {preview.id}  {title}"
    if preview.has_body:
        line += " (...)"
    return line


def render_task_markdown(task: Task) -> str:
    # detail view: full title heading, metadata, verbatim body, subtask lines
    sections: list[str] = []

    meta = [f"# {task.id}: {task.title}", f"status: {task.status.value}"]
    parent_id = task_parent_id(task)
    if parent_id is not None:
        meta.append(f"parent: {parent_id}")
    sections.append("\n".join(meta))

    if task.description is not None:
        sections.append(task.description)

    if task.subtasks:
        child_lines = [
            render_task_line(TaskPreview.from_task(child)) for child in task.subtasks
        ]
        sections.append("## Subtasks\n\n" + "\n".join(child_lines))

    return "\n\n".join(sections)


def render_task_error(ref: str, message: str) -> str:
    # collapse newlines so the result stays a single-line heading
    single_line = " ".join(message.split())
    return f"# {ref}: {single_line}"
