from ._common import get_repo, mcp
from ._model import TaskInfo


@mcp.tool()
def create_task(
    title: str,
    parent: str | None = None,
    description: str | None = None,
) -> TaskInfo:
    """Create a new task. If parent is given, creates a subtask under it."""
    repo = get_repo()

    if parent is None:
        task = repo.create_root_task(
            title=title, description=description, slug=None, extended=False
        )
    else:
        parent_task = repo.resolve_ref(parent)
        task = repo.add_subtask(parent_task, title=title, description=description)

    repo.flush_to_disk()
    return TaskInfo.from_task(task)
