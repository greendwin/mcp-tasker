from tasker.resolve import resolve_ref

from ._common import MutationResult, get_repo, mcp


@mcp.tool()
def create_task(
    title: str,
    parent: str | None = None,
    description: str | None = None,
) -> MutationResult:
    """Create a root task or subtask (when parent is given)."""
    repo = get_repo()

    if parent is None:
        task = repo.create_root_task(
            title=title, description=description, slug=None, extended=False
        )
    else:
        parent_task = resolve_ref(repo, parent).task
        task = repo.add_subtask(parent_task, title=title, description=description)

    repo.flush_to_disk()
    return MutationResult.from_task(task)
