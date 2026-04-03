from pathlib import Path

from tasker.base_types import Task, TaskStatus
from tasker.exceptions import TaskHasSubtasksError
from tasker.parse import ParsedRef

from ._archive_task import (
    archive_root_task_impl,
    is_archived_task_impl,
    unarchive_root_task_impl,
)
from ._move_task import TaskRename, move_task_impl
from ._task_loader import TaskLoader
from ._utils import (
    build_task_path_from_root,
    find_next_root_task_id,
    generate_slug,
    get_next_subtask_id,
    list_root_tasks,
    update_parents_status,
    upgrade_to_filebased,
)


class TaskRepo:
    def __init__(self, root: Path) -> None:
        self.loader = TaskLoader(root)

    @property
    def root(self) -> Path:
        return self.loader.root

    @property
    def archive_root(self) -> Path:
        return self.loader.archive_root

    def resolve_ref(self, task_ref: str) -> Task:
        return self.loader.resolve_ref(task_ref)

    def list_root_tasks(self) -> list[Path]:
        return list_root_tasks(self.root)

    def create_root_task(
        self,
        *,
        title: str,
        description: str | None,
        slug: str | None,
        extended: bool,
    ) -> Task:
        title = _capitalize(title)
        if description is not None:
            description = _capitalize(description)
        root_id = find_next_root_task_id(self.loader)

        if slug is None:
            slug = generate_slug(title)

        task = Task(
            id=root_id,
            slug=slug,
            extended=extended,
            title=title,
            description=description,
        )

        self.loader.register_task(task, original=None)  # new task, no original

        return task

    def add_subtask(
        self,
        parent: Task,
        *,
        title: str,
        description: str | None = None,
        slug: str | None = None,
    ) -> Task:
        title = _capitalize(title)
        if description is not None:
            description = _capitalize(description)

        # upgrade inline task to basic (file-backed) form
        upgrade_to_filebased(parent, loader=self.loader)

        child_id = get_next_subtask_id(parent)

        if description is not None and slug is None:
            # generate slug (i.e. with description task cannot be inline)
            slug = generate_slug(title)

        subtask = Task(
            id=child_id,
            slug=slug,
            title=title,
            description=description,
        )

        parent.subtasks.append(subtask)
        update_parents_status(subtask, loader=self.loader)

        self.loader.register_task(subtask, original=None)

        return subtask

    def start_task(self, task: Task) -> None:
        if task.status == TaskStatus.IN_PROGRESS:
            return

        if not _is_leaf_task(task):
            raise TaskHasSubtasksError(task)

        task.status = TaskStatus.IN_PROGRESS
        update_parents_status(task, loader=self.loader)

    def reset_task(self, task: Task) -> None:
        if not _is_leaf_task(task):
            raise TaskHasSubtasksError(task)

        task.status = TaskStatus.PENDING
        update_parents_status(task, loader=self.loader)

    def cancel_task(self, task: Task, *, force: bool = False) -> list[Task] | None:
        if _is_leaf_task(task):
            task.status = TaskStatus.CANCELLED
            update_parents_status(task, loader=self.loader)
            return None

        if not force:
            raise TaskHasSubtasksError(task)

        closed_tasks: list[Task] = []
        _close_recursive(task, TaskStatus.CANCELLED, closed_tasks)
        update_parents_status(task, loader=self.loader, update_itself=True)
        return closed_tasks[1:]  # don't include root task

    def finish_task(self, task: Task, *, force: bool = False) -> list[Task] | None:
        if _is_leaf_task(task):
            task.status = TaskStatus.DONE
            update_parents_status(task, loader=self.loader)
            return None

        if not force:
            raise TaskHasSubtasksError(task)

        closed_tasks: list[Task] = []
        _close_recursive(task, TaskStatus.DONE, closed_tasks)
        update_parents_status(task, loader=self.loader)
        return closed_tasks[1:]  # don't include root task

    def is_archived_task(self, task_ref: str) -> bool:
        return is_archived_task_impl(self, task_ref)

    def archive_root_task(
        self, task: Task, *, force: bool = False
    ) -> list[Task] | None:
        return archive_root_task_impl(self, task, force=force)

    def unarchive_root_task(self, task_ref: str) -> ParsedRef:
        return unarchive_root_task_impl(self, task_ref)

    def move_task(self, task: Task, *, new_parent: Task | None) -> list[TaskRename]:
        return move_task_impl(
            task,
            new_parent=new_parent,
            loader=self.loader,
        )

    def upgrade_to_filebased(self, task: Task) -> None:
        upgrade_to_filebased(task, loader=self.loader)

    def build_task_path(self, task: Task) -> Path:
        return build_task_path_from_root(task, loader=self.loader)

    def edit_task(
        self,
        task: Task,
        *,
        title: str | None = None,
        description: str | None = None,
        slug: str | None = None,
    ) -> None:
        if title is not None:
            task.title = _capitalize(title)

        if description is not None:
            upgrade_to_filebased(task, loader=self.loader)
            task.description = _capitalize(description)

        if slug is not None:
            task.slug = slug

            # update parents in case of upgrade from inline task
            update_parents_status(task, loader=self.loader)

    def flush_to_disk(self) -> None:
        self.loader.flush_to_disk()


def _capitalize(text: str) -> str:
    return text[:1].upper() + text[1:]


def _is_leaf_task(task: Task) -> bool:
    return task.is_inline or not task.subtasks


def _close_recursive(
    task: Task, new_status: TaskStatus, closed_tasks: list[Task]
) -> None:
    if task.is_closed:
        # already closed — don't override (e.g. don't cancel a done task)
        return

    closed_tasks.append(task)
    task.status = new_status

    for subtask in task.subtasks:
        _close_recursive(subtask, new_status, closed_tasks)
