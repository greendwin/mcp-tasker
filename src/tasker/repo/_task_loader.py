import re
from dataclasses import dataclass
from itertools import chain
from pathlib import Path
from typing import NamedTuple

from tasker.base_types import Task, is_root_task_id, walk_tasks
from tasker.exceptions import TaskNotFoundError, TaskValidateError
from tasker.layout import ARCHIVE_DIR
from tasker.parse import (
    ParsedSubtask,
    TaskDetectResult,
    detect_task_type,
    parse_task,
    parse_task_ref,
    warn_broken_task,
)
from tasker.render import append_task_filename, render_task
from tasker.utils import get_root_task_num, read_text, scan_root_tasks, write_text

from ._utils import (
    build_task_path_from_root,
    update_task_status_and_flags,
)


@dataclass
class OriginalState:
    filename: Path
    content: str
    extended: bool


@dataclass
class RootTaskInfo:
    task_path: Path
    info: TaskDetectResult
    archived: bool


class TaskLoader:
    def __init__(self, root: Path) -> None:
        self.root = root
        self._root_tasks: dict[str, Task] = {}
        self._tasks: dict[str, Task] = {}
        self._original_state: dict[str, OriginalState] = {}

        # pre-cache root tasks info so that we don't need to scan the disk every time
        self._unloaded_root_tasks = _collect_all_root_tasks(root)

    def list_root_tasks(self, *, archived: bool = False) -> list[str]:
        r = []
        for task in self._root_tasks.values():
            if task.archived == archived:
                r.append(task.id)

        for task_info in self._unloaded_root_tasks.values():
            if task_info.archived == archived:
                r.append(task_info.info.task_id)

        return r

    def resolve_ref(self, task_ref: str) -> Task:
        ti = parse_task_ref(task_ref)

        if ti.root_id not in self._root_tasks:
            _load_task_tree(self, ti.root_id, self._unloaded_root_tasks)

        task = self._tasks.get(ti.task_id)
        if task is None:
            raise TaskNotFoundError(
                f"Cannot resolve task reference {task_ref!r}", task_ref=task_ref
            )

        return task

    def get_parent(self, task: Task) -> Task | None:
        if is_root_task_id(task.id):
            return None

        ref = parse_task_ref(task.ref)
        return self.resolve_ref(ref.parent_id)

    def register_task(self, task: Task, original: OriginalState | None) -> None:
        if task.id in self._tasks:
            prev = self._tasks[task.id]
            if prev.title != task.title:
                raise TaskValidateError(
                    f"Task {task.id!r} is registered twice:\n"
                    f"  - {prev.ref}: {prev.title}\n"
                    f"  - {task.ref}: {task.title}",
                    task_ref=task.ref,
                )
            raise TaskValidateError(
                f"Task {task.id!r} was registered twice", task_ref=task.ref
            )

        if is_root_task_id(task.id):
            self._root_tasks[task.id] = task
            self._unloaded_root_tasks.pop(
                task.id, None
            )  # drop: it's not unloaded anymore

        self._tasks[task.id] = task

        if original:
            self._original_state[task.id] = original

    def reregister_task(self, task: Task, prev_id: str) -> None:
        assert prev_id in self._tasks, f"task {prev_id!r} is not registered"
        assert task.id not in self._tasks, f"task {task.id!r} is already registered"

        del self._tasks[prev_id]
        self._tasks[task.id] = task

        if prev_id in self._root_tasks:
            del self._root_tasks[prev_id]
        if is_root_task_id(task.id):
            self._root_tasks[task.id] = task

        orig = self._original_state.pop(prev_id, None)
        if orig is not None:
            self._original_state[task.id] = orig

    def check_task_changed(self, task: Task) -> bool:
        assert task.slug, "trying to test inline task"

        task_path = build_task_path_from_root(task, loader=self)
        content = read_text(task_path)

        orig = self._original_state.get(task.id)
        if orig and orig.content == content and orig.filename == task_path:
            return False

        return True

    def get_tasks_root(self, *, archived: bool = False) -> Path:
        if archived:
            return self.root / ARCHIVE_DIR
        return self.root

    def find_next_root_task_id(self) -> str:
        max_idx = None
        for task_id in chain(self._root_tasks, self._unloaded_root_tasks):
            idx = get_root_task_num(task_id)
            if max_idx is None or max_idx < idx:
                max_idx = idx

        return f"s{(max_idx or 0) + 1:02d}"

    def reload_root_tree(self, root_id: str) -> None:
        assert root_id in self._root_tasks

        fresh = TaskLoader(self.root)
        _load_task_tree(fresh, root_id, fresh._unloaded_root_tasks)

        fresh_root = fresh._root_tasks.get(root_id)
        existing_root = self._root_tasks[root_id]

        if fresh_root is None:
            raise NotImplementedError("Trying to reload task tree after add/remove")

        _merge_task(existing_root, fresh_root)

        for t in walk_tasks(existing_root):
            orig = fresh._original_state.get(t.id)
            if orig is not None:
                self._original_state[t.id] = orig

    def flush_to_disk(self) -> None:
        pending_dir_cleanups: list[_PendingDirCleanup] = []
        for task in self._root_tasks.values():
            _flush_task(
                self.get_tasks_root(archived=task.archived),
                task,
                original_state=self._original_state,
                pending_dir_cleanups=pending_dir_cleanups,
            )

        _cleanup_old_dirs(pending_dir_cleanups)


def _collect_all_root_tasks(root: Path) -> dict[str, RootTaskInfo]:
    paths: list[RootTaskInfo] = []
    for task_path in scan_root_tasks(root):
        if tp := detect_task_type(task_path):
            paths.append(RootTaskInfo(task_path, tp, False))

    for task_path in scan_root_tasks(root / ARCHIVE_DIR):
        if tp := detect_task_type(task_path):
            paths.append(RootTaskInfo(task_path, tp, True))

    # check for duplicated paths
    result: dict[str, RootTaskInfo] = {}
    for p in paths:
        if p.info.task_id in result:
            raise TaskValidateError(
                f"Ambiguous task `{p.info.task_id}`: multiple files match:\n"
                f"  - {result[p.info.task_id].task_path.name}\n"
                f"  - {p.task_path.name}",
                task_ref=p.info.task_id,
            )

        result[p.info.task_id] = p

    return result


def _normalize_body(text: str | None) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _verify_render_faithful(task: Task, rendered: str) -> None:
    # Re-parse the just-rendered output and compare it against the in-memory task.
    # A serialization that drops or mangles the round-tripped fields must abort
    # the flush loudly instead of silently overwriting the on-disk file.
    #
    # Title, status, and the free-prose body are all re-derived by parsing, so
    # all three are checked here; a future round-trip field must consciously
    # extend this guard to be protected.
    assert task.slug is not None, "render guard only runs for file-backed tasks"

    reparsed, _ = parse_task(
        rendered,
        task_id=task.id,
        slug=task.slug,
        extended=task.extended,
    )

    if reparsed.title != task.title or reparsed.status != task.status:
        raise TaskValidateError(
            f"Rendering task {task.ref!r} would lose title/status; "
            f"refusing to overwrite the existing file",
            task_ref=task.ref,
        )

    if _normalize_body(reparsed.description) != _normalize_body(task.description):
        raise TaskValidateError(
            f"Rendering task {task.ref!r} would lose body content; "
            f"refusing to overwrite the existing file",
            task_ref=task.ref,
        )


class _PendingDirCleanup(NamedTuple):
    old_dir: Path
    task_id: str


def _flush_task(
    parent_dir: Path,
    task: Task,
    *,
    original_state: dict[str, OriginalState],
    pending_dir_cleanups: list[_PendingDirCleanup],
) -> None:
    orig = original_state.get(task.id)

    if task.is_inline:
        assert task.order is None, "ordered task must be upgraded to file-based first"

    new_filename: Path | None = None
    if not task.is_inline and not task.deleted:
        rendered = render_task(task)
        new_filename = append_task_filename(parent_dir, task.ref, task.extended)

        if orig is None or new_filename != orig.filename or rendered != orig.content:
            _verify_render_faithful(task, rendered)
            write_text(new_filename, rendered)

            original_state[task.id] = OriginalState(
                filename=new_filename,
                content=rendered,
                extended=task.extended,
            )

    # recursively flush file-backed subtasks
    subtask_root = parent_dir / task.ref
    for child in task.subtasks:
        _flush_task(
            subtask_root,
            child,
            original_state=original_state,
            pending_dir_cleanups=pending_dir_cleanups,
        )

    if orig is None:
        # new file, nothing to delete
        return

    if not task.deleted and new_filename == orig.filename:
        return

    # remove old filename
    if orig.filename.exists():
        orig.filename.unlink()

    if orig.extended:
        # defer directory cleanup — other root tasks may still need to
        # clean up their old files from this directory first
        old_dir = orig.filename.parent
        pending_dir_cleanups.append(_PendingDirCleanup(old_dir, task.id))


def _cleanup_old_dirs(dirs: list[_PendingDirCleanup]) -> None:
    # Process deepest directories first so nested dirs are removed
    # before their parents.
    dirs.sort(key=lambda item: len(item[0].parts), reverse=True)
    for old_dir, task_id in dirs:
        if not old_dir.exists():
            continue

        dir_content = next(old_dir.iterdir(), None)
        if dir_content is not None:
            raise TaskValidateError(
                f"Old task directory {old_dir.name!r} contains "
                f"non-task files (e.g. {dir_content.name!r}) "
                f"and cannot be removed automatically",
                task_ref=task_id,
            )

        old_dir.rmdir()


def _load_task_tree(
    loader: TaskLoader, root_id: str, unloaded_root_tasks: dict[str, RootTaskInfo]
) -> None:
    task_info = unloaded_root_tasks.get(root_id)
    if task_info is None:
        raise TaskValidateError(f"Task {root_id!r} not found", task_ref=root_id)

    tt = task_info.info
    content = read_text(tt.content_path)

    try:
        root, subtasks = parse_task(
            content,
            task_id=tt.task_id,
            slug=tt.slug,
            extended=tt.extended,
        )
    except TaskValidateError as ex:
        if ex.file_path is None:
            ex.file_path = tt.content_path.relative_to(loader.root)
        raise

    assert root_id == root.id
    root.archived = task_info.archived

    orig_info = OriginalState(
        filename=tt.content_path,
        content=content,
        extended=tt.extended,
    )
    loader.register_task(root, orig_info)

    search_dir = loader.get_tasks_root(archived=task_info.archived)
    for child_info in subtasks:
        child = _load_subtask(
            # note: use original `tt.task_ref`, `task.ref` can be changed from file
            search_dir / tt.task_ref,
            child_info,
            loader=loader,
            archived=task_info.archived,
        )
        if child is not None:
            root.subtasks.append(child)

    _invalidate_task_flags(root)


def _load_subtask(
    parent_dir: Path,
    task_info: ParsedSubtask,
    *,
    loader: TaskLoader,
    archived: bool,
) -> Task | None:
    if task_info.slug is None:
        # inline task cannot be extended
        assert not task_info.extended
        task = Task(
            id=task_info.id,
            title=task_info.title,
            status=task_info.status,
            slug=task_info.slug,
            extended=task_info.extended,
            archived=archived,
        )

        assert task.is_inline
        loader.register_task(task, original=None)  # no original source for inline tasks
        return task

    original_path = append_task_filename(parent_dir, task_info.ref, task_info.extended)

    if task_info.extended and not original_path.exists():
        warn_broken_task(original_path)
        return None

    content = read_text(original_path)

    try:
        task, subtasks = parse_task(
            content,
            task_id=task_info.id,
            slug=task_info.slug,
            extended=task_info.extended,
        )
    except TaskValidateError as ex:
        if ex.file_path is None:
            ex.file_path = original_path.relative_to(loader.root)
        raise

    task.archived = archived

    orig_info = OriginalState(
        filename=original_path,
        content=content,
        extended=task_info.extended,
    )
    loader.register_task(task, orig_info)

    # note: use original `task_info.ref`, since `task.ref` could be changed
    # already by `slug` override
    subtasks_dir = parent_dir / task_info.ref
    for child_info in subtasks:
        child = _load_subtask(
            subtasks_dir, child_info, loader=loader, archived=archived
        )
        if child is not None:
            task.subtasks.append(child)

    return task


def _merge_task(existing: Task, fresh: Task) -> None:
    assert existing.id == fresh.id

    existing.title = fresh.title
    existing.status = fresh.status
    existing.slug = fresh.slug
    existing.extended = fresh.extended
    existing.description = fresh.description
    existing.deleted = fresh.deleted
    existing.archived = fresh.archived

    # subtasks list is intentionally not mutated: structural changes
    #  must go through tasker commands
    #
    # note: if the user edited the file to add/remove subtasks,
    # drop those edits silently — the next flush will rewrite them
    if [c.id for c in existing.subtasks] != [c.id for c in fresh.subtasks]:
        return

    for ec, fc in zip(existing.subtasks, fresh.subtasks):
        _merge_task(ec, fc)


def _invalidate_task_flags(task: Task) -> None:
    if task.is_inline:
        assert not task.extended
        return

    for child in task.subtasks:
        _invalidate_task_flags(child)

    # update root itself
    update_task_status_and_flags(task, allow_downgrade=False)
