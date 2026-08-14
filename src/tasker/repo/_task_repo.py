from pathlib import Path

from tasker.base_types import Task, TaskStatus, walk_tasks
from tasker.exceptions import TaskHasSubtasksError, TaskNotFoundError
from tasker.parse import ParsedRef, parse_task_ref

from ._move_task import (
    TaskRename,
    archive_root_task_impl,
    delete_task_impl,
    move_task_impl,
    unarchive_root_task_impl,
)
from ._task_loader import TaskLoader
from ._utils import (
    build_task_path_from_root,
    generate_slug,
    get_next_subtask_id,
    update_parents_status,
    upgrade_to_filebased,
)


class TaskRepo:
    def __init__(self, root: Path) -> None:
        self.loader = TaskLoader(root)

    @property
    def root(self) -> Path:
        return self.loader.root

    def resolve_ref(self, task_ref: str) -> Task:
        return self.loader.resolve_ref(task_ref)

    def get_parent(self, task: Task) -> Task | None:
        return self.loader.get_parent(task)

    def try_resolve_ref(self, task_ref: str) -> Task | None:
        try:
            return self.loader.resolve_ref(task_ref)
        except TaskNotFoundError:
            return None

    def list_root_tasks(self, *, archived: bool = False) -> list[str]:
        return self.loader.list_root_tasks(archived=archived)

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
        root_id = self.loader.find_next_root_task_id()

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

    def review_task(self, task: Task) -> None:
        if task.status == TaskStatus.IN_REVIEW:
            return

        if not _is_leaf_task(task):
            raise TaskHasSubtasksError(task)

        task.status = TaskStatus.IN_REVIEW
        update_parents_status(task, loader=self.loader)

    def reset_task(self, task: Task, *, force: bool = False) -> list[Task] | None:
        if task.status == TaskStatus.PENDING:
            assert all(t.status == TaskStatus.PENDING for t in task.subtasks)
            return None

        if _is_leaf_task(task):
            task.status = TaskStatus.PENDING
            update_parents_status(task, loader=self.loader)
            return None

        if not force:
            raise TaskHasSubtasksError(task)

        reset_tasks: list[Task] = []
        _reset_recursive(task, reset_tasks)
        update_parents_status(task, loader=self.loader, update_itself=True)
        return reset_tasks[1:]  # don't include root task

    def cancel_task(self, task: Task, *, force: bool = False) -> list[Task] | None:
        if task.status == TaskStatus.CANCELLED:
            # already cancelled
            assert all(t.is_closed for t in task.subtasks)
            return None

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
        if task.status == TaskStatus.DONE:
            return None

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

    def archive_root_task(
        self, task: Task, *, force: bool = False
    ) -> list[Task] | None:
        return archive_root_task_impl(self, task, force=force)

    def unarchive_root_task(self, task_ref: str) -> ParsedRef:
        return unarchive_root_task_impl(self, task_ref)

    def move_task(
        self, task: Task, *, new_parent: Task | None, new_id: str | None = None
    ) -> list[TaskRename]:
        return move_task_impl(
            task,
            new_parent=new_parent,
            new_id=new_id,
            loader=self.loader,
        )

    def delete_task(self, task: Task) -> None:
        delete_task_impl(task, loader=self.loader)

    def upgrade_to_filebased(self, task: Task) -> None:
        upgrade_to_filebased(task, loader=self.loader)

    def try_downgrade_task(self, task: Task) -> None:
        update_parents_status(
            task, loader=self.loader, update_itself=True, allow_downgrade=True
        )

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

    def reload_root_tree(self, task: Task) -> None:
        # note: accept any task and reload its roots
        ref = parse_task_ref(task.ref)
        self.loader.reload_root_tree(ref.root_id)

    def flush_to_disk(self) -> None:
        self.loader.flush_to_disk()


def _capitalize(text: str) -> str:
    return text[:1].upper() + text[1:]


def _is_leaf_task(task: Task) -> bool:
    return task.is_inline or not task.subtasks


def _close_recursive(
    task: Task, new_status: TaskStatus, closed_tasks: list[Task]
) -> None:
    for t in walk_tasks(task):
        if not t.is_closed:
            closed_tasks.append(t)
            t.status = new_status


def _reset_recursive(task: Task, reset_tasks: list[Task]) -> None:
    for t in walk_tasks(task):
        if t.status != TaskStatus.PENDING:
            reset_tasks.append(t)
            t.status = TaskStatus.PENDING
