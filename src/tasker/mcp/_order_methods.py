from tasker.base_types import Task
from tasker.exceptions import TaskerError, TaskValidateError
from tasker.repo import TaskRepo, group_at_anchor
from tasker.resolve import resolve_ref

from ._common import MutationResult, get_repo, mcp


@mcp.tool()
def order_tasks(task_refs: list[str]) -> MutationResult:
    """Group same-parent siblings contiguously, anchor first, in the given order.

    The first ref is the anchor; the rest are placed after it in argument order.
    All refs must be siblings under the same parent -- a cross-parent ref is
    rejected (this tool never moves tasks between parents). Returns the concise
    ack for the anchor.
    """
    if len(task_refs) < 2:
        raise TaskerError(
            "At least two arguments must be provided to order them properly"
        )

    repo = get_repo()

    resolved = [resolve_ref(repo, ref) for ref in task_refs]
    anchor, *moved = (r.task for r in resolved)

    anchor_parent = repo.get_parent(anchor)
    for task in moved:
        if repo.get_parent(task) is not anchor_parent:
            raise TaskValidateError(
                f"Task {task.id!r} is not a sibling of anchor {anchor.id!r}.",
                task_ref=task.id,
            )

    if moved:
        repo.upgrade_to_filebased(anchor)
        for task in moved:
            repo.upgrade_to_filebased(task)

        siblings = _collect_siblings(repo, anchor_parent)
        group_at_anchor(siblings, anchor_id=anchor.id, moved_ids=[t.id for t in moved])
        repo.flush_to_disk()

    return MutationResult.from_task(anchor)


def _collect_siblings(repo: TaskRepo, parent: Task | None) -> list[Task]:
    if parent is not None:
        return [p for p in parent.subtasks if not p.deleted]

    return [repo.resolve_ref(task_id) for task_id in repo.list_root_tasks()]
