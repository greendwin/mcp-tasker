from tasker.exceptions import TaskValidateError
from tasker.parse import parse_task_file
from tasker.resolve import resolve_ref
from tasker.todo import classify_todo, load_todo_tasks

from ._common import get_repo, mcp
from ._render import (
    TASK_BLOCK_SEPARATOR,
    render_task_error,
    render_task_line,
    render_task_markdown,
)


@mcp.tool()
def list_tasks(todo: bool = False) -> str:
    """
    List root tasks as compact lines: ``<sign> <id>  <title> (...)``.

    Status signs: ``.`` pending, ``~`` in-progress, ``?`` in-review,
    ``x`` done, ``-`` cancelled. A trailing ``(...)`` marks a task that has
    a body -- view it for the full detail.

    Args:
        todo: If True, list only tasks from the TODO list.
    """
    repo = get_repo()

    if todo:
        view = classify_todo(load_todo_tasks(repo))
        if view.all_finished:
            return "All tasks finished!"
        tasks = view.active
    else:
        tasks = [parse_task_file(p).task for p in repo.list_root_tasks()]

    lines = [render_task_line(t) for t in tasks]
    return "\n".join(lines) if lines else "No tasks"


@mcp.tool()
def view_tasks(task_refs: list[str]) -> str:
    """View tasks by IDs as trimmed markdown.

    Each task renders as ``# <id>: <full title>`` followed by ``status:`` /
    ``parent:`` metadata lines (``parent:`` omitted for root tasks), the
    verbatim task body, and a ``## Subtasks`` checklist reusing the compact
    line format. A bad/deleted/unknown ref becomes a ``# <ref>: <error>`` stub
    instead of failing the batch. Blocks are joined by ``\\n\\n---\\n\\n``.

    Use this instead of reading task files from disk.
    """
    repo = get_repo()
    blocks: list[str] = []

    for ref in task_refs:
        try:
            task = resolve_ref(repo, ref).task
            blocks.append(render_task_markdown(task))
        except TaskValidateError as exc:
            blocks.append(render_task_error(ref, str(exc)))

    return TASK_BLOCK_SEPARATOR.join(blocks)
