from collections import defaultdict
from dataclasses import dataclass, field
from enum import IntEnum
from typing import TypeAlias

from tasker.base_types import Task, TaskStatus
from tasker.repo import TaskRepo
from tasker.resolve import load_recent_task
from tasker.todo import assign_todo_letters, load_todo_list, resolve_todo_tasks
from tasker.utils import console, escape_markup

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
    markers: list[str] | None
    highlight: bool


# note: higher values expand more children
class ShowChildrenMode(IntEnum):
    MANUAL = 1
    SHOW_OPENED = 2
    SHOW_ALL = 3


class ShowTaskConfig:
    def __init__(
        self,
        *,
        show_task_id: bool,
        show_pending_marker: bool,
    ) -> None:
        self.tasks: dict[str, Task] = {}
        self.highlight: set[str] = set()
        self.show_children_mode: dict[str, ShowChildrenMode] = {}
        self.show_task_id = show_task_id
        self.show_pending_marker = show_pending_marker

    def show_task(
        self,
        task: Task,
        show_children_mode: ShowChildrenMode = ShowChildrenMode.MANUAL,
        *,
        highlight: bool = False,
    ) -> None:
        self.tasks[task.id] = task
        if highlight:
            self.highlight.add(task.id)

        prev_mode = self.show_children_mode.get(task.id)
        if prev_mode is None or show_children_mode > prev_mode:
            self.show_children_mode[task.id] = show_children_mode


MarkersDict: TypeAlias = dict[str, list[str]]


@dataclass
class _CollectContext:
    entries: list[PrintEntry] = field(default_factory=list)
    visible: dict[str, Task] = field(default_factory=dict)
    highlight: set[str] = field(default_factory=set)
    markers: MarkersDict = field(default_factory=dict)


def compute_markers(repo: TaskRepo, *visible: Task) -> MarkersDict:
    markers: MarkersDict = defaultdict(list)

    todo = load_todo_list(repo)
    todo_tasks = resolve_todo_tasks(repo, todo)
    todo_ids = {t.id for t in todo_tasks}
    letters = assign_todo_letters(todo_tasks)
    for t in visible:
        if t.id in todo_ids:
            letter = letters.get(t.id)
            markers[t.id].append(f"({letter})" if letter else "(todo)")

    recent = load_recent_task(repo)
    if recent:
        visible_ids = {t.id for t in visible}
        recent_marker = _find_recent_marker(repo, recent, visible_ids)
        if recent_marker:
            task_id, marker = recent_marker
            markers[task_id].append(marker)

    return markers


def _find_recent_marker(
    repo: TaskRepo, recent: Task, visible_ids: set[str]
) -> tuple[str, str] | None:
    if recent.id in visible_ids:
        return recent.id, "(q)"

    parent = repo.get_parent(recent)
    depth = 1
    while parent:
        if parent.id in visible_ids:
            return parent.id, f"({'p' * depth})"

        parent = repo.get_parent(parent)
        depth += 1

    return None


def print_tree(repo: TaskRepo, config: ShowTaskConfig) -> None:
    entries = _build_print_entries(repo, config)

    _print_tree_entries(
        entries,
        show_task_id=config.show_task_id,
        show_pending_marker=config.show_pending_marker,
    )


def _build_print_entries(repo: TaskRepo, config: ShowTaskConfig) -> list[PrintEntry]:
    ctx = _CollectContext(
        highlight=config.highlight,
    )

    has_force_show = set()
    for task in config.tasks.values():
        cur: Task | None = task
        while cur:
            has_force_show.add(cur.id)
            cur = repo.get_parent(cur)

    walked: dict[str, ShowChildrenMode] = {}
    for task in config.tasks.values():
        _collect_visible_tasks(
            ctx.visible,
            task,
            config.show_children_mode.get(task.id, ShowChildrenMode.MANUAL),
            walked=walked,
            has_force_show=has_force_show,
        )

    visible_roots: dict[str, Task] = {}
    for task in ctx.visible.values():
        cur = task
        while True:
            parent = repo.get_parent(cur)
            # walk to closest visible ancestor
            if parent is None or parent.id not in ctx.visible:
                visible_roots[cur.id] = cur
                break
            cur = parent

    ctx.markers = compute_markers(repo, *ctx.visible.values())

    for root in sorted(visible_roots.values()):
        _collect_print_entries(ctx, root, indent=0)

    return ctx.entries


def _collect_visible_tasks(
    visible: dict[str, Task],
    cur: Task,
    mode: ShowChildrenMode,
    *,
    walked: dict[str, ShowChildrenMode],
    has_force_show: set[str],
) -> None:
    if cur.id in walked and walked[cur.id] >= mode:
        return

    walked[cur.id] = mode
    visible[cur.id] = cur

    for child in cur.subtasks:
        if child.id not in has_force_show:
            match mode:
                case ShowChildrenMode.MANUAL:
                    continue
                case ShowChildrenMode.SHOW_OPENED:
                    if child.is_closed:
                        continue
                case _:
                    assert mode == ShowChildrenMode.SHOW_ALL

        _collect_visible_tasks(
            visible,
            child,
            mode,
            walked=walked,
            has_force_show=has_force_show,
        )


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
        markers=ctx.markers.get(task.id),
        highlight=task.id in ctx.highlight,
    )
    ctx.entries.append(entry)

    for child in sorted(task.subtasks):
        if child.id in ctx.visible:
            _collect_print_entries(ctx, child, indent=indent + 1)


def _print_tree_entries(
    entries: list[PrintEntry],
    *,
    show_task_id: bool,
    show_pending_marker: bool,
) -> None:
    for p in entries:
        line = format_task_list_item(
            p.task,
            show_task_id=show_task_id,
            show_pending_marker=show_pending_marker,
            indent=p.indent,
            highlight=p.highlight,
            markers=p.markers,
            show_subtask_count=False,
        )
        console.print(line)


def format_task_list_item(
    task: Task,
    *,
    show_task_id: bool = True,
    show_pending_marker: bool = False,
    indent: int = 0,
    highlight: bool = False,
    markers: list[str] | None = None,
    show_subtask_count: bool = False,
) -> str:
    r = []

    if indent > 0:
        r.append("  " * indent)
        r.append("- ")

    id_color = "blue"
    id_suffix_color = "slate_blue3"
    if task.deleted:
        id_color = "red"
        id_suffix_color = "red"
    elif task.status == TaskStatus.CANCELLED:
        # override task_id by status color
        id_color = _STATUS_COLOR[task.status]
        id_suffix_color = _STATUS_COLOR[task.status]

    if show_task_id:
        if len(task.id) <= 3:
            # don't highlight digits in stories aka `s01` - it's short enough
            r.append(f"[{id_color}]{task.id}[/{id_color}]")
        else:
            id_prefix = task.id[:-2]
            r.append(f"[{id_color}]{id_prefix}[/{id_color}]")

            id_suffix = task.id[-2:]
            r.append(f"[{id_suffix_color}]{id_suffix}[/{id_suffix_color}]")

        r.append(": ")

    # note: omit `[ ]` for pending tasks unless when `--all` is used
    show_marker = show_pending_marker or task.status != TaskStatus.PENDING

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

    r.append(escape_markup(task.title))

    if color_override:
        r.append(f"[/{color_override}]")

    if show_subtask_count:
        total = _count_subtasks(task)
        if total > 0:
            r.append(f" [dim](+{total} subtasks)[/dim]")

    if markers:
        for mark in markers:
            r.append(f" [cyan]{mark}[/cyan]")

    if highlight:
        r.append(" [bright_yellow]<<<[/bright_yellow]")

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


def print_task(task: Task, *, markers: MarkersDict, preview: bool) -> None:
    item = format_task_list_item(
        task,
        show_task_id=not preview,
        show_pending_marker=preview,
        markers=markers.get(task.id),
    )

    if preview:
        console.print("")
    console.print(item)

    # note: show the task body in a compact way
    if task.description:
        if not preview:
            console.print("")
        console.print(escape_markup(task.description))

    if preview or not task.subtasks:
        return

    console.print("\n[bold]Subtasks:[/bold]")
    for subtask in sorted(task.subtasks):
        item = format_task_list_item(
            subtask,
            indent=1,
            show_subtask_count=True,
            markers=markers.get(subtask.id),
        )
        console.print(item)


@dataclass(slots=True)
class ActionReportItem:
    task_id: str
    title: str
    outcome: str | None


class ActionReportConfig:
    def __init__(self) -> None:
        self.items: list[ActionReportItem] = []

    def add_task(self, task: Task, *, outcome: str | None = None) -> ActionReportItem:
        return self.add_item(task.id, task.title, outcome=outcome)

    def add_item(
        self, task_id: str, title: str, *, outcome: str | None = None
    ) -> ActionReportItem:
        item = ActionReportItem(task_id, title, outcome)
        self.items.append(item)
        return item


def print_action_report(title: str, config: ActionReportConfig) -> None:
    if not config.items:
        return

    console.print("{}:".format(escape_markup(title)))
    for p in config.items:
        if not p.outcome:
            console.print("  - [cyan]{:8}[/cyan]".format(escape_markup(p.task_id)))
            continue

        console.print(
            "  - [cyan]{:8}[/cyan] [dim]({})[/dim]".format(
                escape_markup(p.task_id), escape_markup(p.outcome)
            )
        )


def print_parents_with_opened(
    repo: TaskRepo, *tasks: Task, highlight: bool | set[str]
) -> None:
    if not tasks:
        return

    console.print("")

    config = ShowTaskConfig(
        show_task_id=True,
        show_pending_marker=False,
    )

    has_open_ancestor = False

    for task in tasks:
        config.show_task(
            task,
            ShowChildrenMode.SHOW_OPENED,
            highlight=is_highlighted(task, highlight),
        )

        ancestor = repo.get_parent(task)
        while ancestor:
            config.show_task(
                ancestor,
                ShowChildrenMode.SHOW_OPENED,
            )
            if not ancestor.is_closed:
                has_open_ancestor = True
                break
            ancestor = repo.get_parent(ancestor)

    if not has_open_ancestor and all(t.is_closed for t in tasks):
        for task_id in repo.list_root_tasks():
            root = repo.resolve_ref(task_id)
            if not root.is_closed:
                config.show_task(root, ShowChildrenMode.SHOW_OPENED)

    print_tree(repo, config)


def print_parents_only(
    repo: TaskRepo,
    *tasks: Task,
    highlight: bool | set[str],
    show_pending_marker: bool = False,
    show_children_mode: ShowChildrenMode = ShowChildrenMode.SHOW_OPENED,
) -> None:
    if not tasks:
        return

    console.print("")

    config = ShowTaskConfig(
        show_task_id=True,
        # TODO: test me!
        show_pending_marker=show_pending_marker,
    )

    for task in tasks:
        config.show_task(
            task,
            show_children_mode,
            highlight=is_highlighted(task, highlight),
        )

        ancestor = repo.get_parent(task)
        while ancestor:
            config.show_task(ancestor)
            ancestor = repo.get_parent(ancestor)

    print_tree(repo, config)


def is_highlighted(task: Task, highlight: bool | set[str]) -> bool:
    if not isinstance(highlight, set):
        return highlight

    return task.id in highlight
