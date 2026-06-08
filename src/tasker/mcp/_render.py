from tasker.base_types import TaskStatus
from tasker.mcp._model import TaskPreview

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
