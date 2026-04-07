from collections.abc import Sequence
from dataclasses import dataclass, field
from itertools import chain

from tasker.base_types import Task, TaskStatus
from tasker.cli._resolve_task import load_recent_task
from tasker.repo import TaskRepo
from tasker.utils import console

_STATUS_COLOR = {
    TaskStatus.PENDING: "white",
    TaskStatus.IN_PROGRESS: "bright_blue",
    TaskStatus.IN_REVIEW: "bright_blue",
    TaskStatus.DONE: "green",
    TaskStatus.CANCELLED: "bright_black",
}

_STATUS_MARKER = {
    TaskStatus.PENDING: r"\[ ]",
    TaskStatus.IN_PROGRESS: r"\[~]",
    TaskStatus.IN_REVIEW: r"\[~]",
    TaskStatus.DONE: r"\[x]",
    TaskStatus.CANCELLED: r"\[x]",
}


@dataclass(slots=True)
class PrintEntry:
    task: Task
    indent: int
    marker: str | None
    highlight: bool


def build_print_entries(
    repo: TaskRepo,
    *,
    # list of tasks which subtrees must be shown (aka top-to-bottom)
    root_tasks: Sequence[Task],
    # list of tasks that must be shown and highlighted (aka bottom-to-top)
    highlight_tasks: Sequence[Task],
    # whether to show closed tasks
    show_closed: bool,
) -> list[PrintEntry]:
    # list of roots provided by highlights
    highlight_roots: list[Task] = []

    # tells whether this task has highlight in its childs
    has_highlight: set[str] = set()

    ctx = _CollectContext()

    # iter highlighted tasks and collect common roots for them
    for task in highlight_tasks:
        ctx.highlighted.add(task.id)

        # TBD: should we do this logic here?
        if parent := repo.get_parent(task):
            highlight_roots.append(parent)
        else:
            highlight_roots.append(task)

        # mark whole parents chain
        cur: Task | None = task
        while cur:
            has_highlight.add(cur.id)
            cur = repo.get_parent(cur)

    # walk from root tasks down and mark visible tasks
    for task in chain(root_tasks, highlight_roots):
        _collect_visible_tasks(
            task,
            ctx.visible,
            show_closed=show_closed,
            has_highlight=has_highlight,
        )

    visible_roots: dict[str, Task] = {}
    for task in ctx.visible.values():
        cur = task
        while True:
            parent = repo.get_parent(cur)
            if parent is None or parent.id not in ctx.visible:
                visible_roots[cur.id] = cur
                break

            cur = parent

    ctx.markers = compute_markers(repo, *ctx.visible.values())

    for root in sorted(visible_roots.values(), key=lambda p: p.id):
        _collect_print_entries(ctx, root, indent=0)

    return ctx.entries


@dataclass
class _CollectContext:
    entries: list[PrintEntry] = field(default_factory=list)
    visible: dict[str, Task] = field(default_factory=dict)
    highlighted: set[str] = field(default_factory=set)
    markers: dict[str, str] = field(default_factory=dict)


def _collect_visible_tasks(
    cur: Task, visible: dict[str, Task], *, show_closed: bool, has_highlight: set[str]
) -> None:
    if cur.id in visible:
        # already processed
        return

    visible[cur.id] = cur

    for child in cur.subtasks:
        if child.is_closed and not show_closed and child.id not in has_highlight:
            continue

        _collect_visible_tasks(
            child,
            visible,
            show_closed=show_closed,
            has_highlight=has_highlight,
        )


def compute_markers(repo: TaskRepo, *visible: Task) -> dict[str, str]:
    recent = load_recent_task(repo)
    if not recent:
        return {}

    visible_ids = {t.id for t in visible}

    if recent.id in visible_ids:
        return {recent.id: "(q)"}

    parent = repo.get_parent(recent)
    depth = 1
    while parent:
        if parent.id in visible_ids:
            return {parent.id: f"({'p' * depth})"}

        parent = repo.get_parent(parent)
        depth += 1

    return {}


def _collect_print_entries(
    ctx: _CollectContext,
    task: Task,
    *,
    indent: int,
) -> None:
    assert task.id in ctx.visible

    entry = PrintEntry(
        task=task,
        indent=indent,
        marker=ctx.markers.get(task.id),
        highlight=task.id in ctx.highlighted,
    )
    ctx.entries.append(entry)

    for child in task.subtasks:
        if child.id in ctx.visible:
            _collect_print_entries(ctx, child, indent=indent + 1)


def print_tree_entries(
    entries: list[PrintEntry], *, show_all: bool, show_task_id: bool = True
) -> None:
    for p in entries:
        line = format_task_list_item(
            p.task,
            show_task_id=show_task_id,
            show_all=show_all,
            indent=p.indent,
            highlight=p.highlight,
            marker=p.marker,
            show_subtask_count=False,  # TODO
        )
        console.print(line)


def format_task_list_item(
    task: Task,
    *,
    show_task_id: bool = True,
    show_all: bool = False,
    indent: int = 0,
    highlight: bool = False,
    marker: str | None = None,
    show_subtask_count: bool = False,
) -> str:
    r = []

    if indent > 0:
        r.append("  " * indent)
        r.append("- ")

    id_color = "blue"
    if task.deleted:
        id_color = "red"
    elif task.status == TaskStatus.CANCELLED:
        # override task_id by status color
        id_color = _STATUS_COLOR[task.status]

    if show_task_id:
        r.append(f"[{id_color}]")
        r.append(task.id)
        r.append(f"[/{id_color}]")
        r.append(": ")

    # note: omit `[ ]` for pending tasks unless when `--all` is used
    show_marker = show_all or task.status != TaskStatus.PENDING

    color_override: str | None = None
    if task.status == TaskStatus.CANCELLED:
        color_override = _STATUS_COLOR[task.status]

    if color_override:
        r.append(f"[{color_override}]")

    if show_marker:
        r.append(_task_marker(task, colored=not color_override))
        r.append(" ")

    if task.status == TaskStatus.IN_REVIEW:
        r.append("[bold cyan]**review**[/bold cyan] ")

    r.append(task.title)

    if color_override:
        r.append(f"[/{color_override}]")

    if show_subtask_count:
        total = _count_subtasks(task)
        if total > 0:
            r.append(f" [dim](+{total} subtasks)[/dim]")

    if highlight:
        r.append(" [bright_yellow]<<<[/bright_yellow]")

    if marker:
        r.append(f" [cyan]{marker}[/cyan]")

    return "".join(r)


def _task_marker(task: Task, *, colored: bool) -> str:
    if not colored:
        return _STATUS_MARKER[task.status]

    color = _STATUS_COLOR[task.status]
    marker = _STATUS_MARKER[task.status]
    return f"[{color}]{marker}[/{color}]"


def _count_subtasks(task: Task) -> int:
    count = len(task.subtasks)
    for child in task.subtasks:
        if child.subtasks:
            count += _count_subtasks(child)
    return count


def print_task(task: Task, *, markers: dict[str, str], preview: bool) -> None:
    item = format_task_list_item(
        task,
        show_task_id=not preview,
        show_all=preview,
        marker=markers.get(task.id),
    )

    if preview:
        console.print("")
    console.print(f"{item}")

    # note: show description and extra section in compact way
    if task.description:
        if not preview:
            console.print("")
        console.print(f"{task.description}")

    if task.extra_sections:
        if task.description or not preview:
            console.print("")
        console.print(f"{task.extra_sections}")

    if preview or not task.subtasks:
        return

    console.print("\n[bold]Subtasks:[/bold]")
    for subtask in task.subtasks:
        item = format_task_list_item(
            subtask,
            indent=1,
            show_subtask_count=True,
            marker=markers.get(subtask.id),
        )
        console.print(item)


def print_tree(
    repo: TaskRepo,
    *,
    roots: Sequence[Task],
    highlight: Sequence[Task],
    show_all: bool,
) -> None:
    entries = build_print_entries(
        repo,
        root_tasks=roots,
        highlight_tasks=highlight,
        show_closed=show_all,
    )

    print_tree_entries(entries, show_all=show_all)


def print_parent_preview(repo: TaskRepo, *tasks: Task) -> None:
    if not tasks:
        return

    # TODO: move this line outside
    console.print("")

    print_tree(repo, roots=(), highlight=tasks, show_all=False)
