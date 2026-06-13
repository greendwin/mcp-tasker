from collections.abc import Iterable
from typing import Any

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field, model_serializer
from pydantic_core.core_schema import SerializerFunctionWrapHandler
from typing_extensions import Self

from tasker.base_types import Task, TaskStatus
from tasker.layout import discover_tasker_dir
from tasker.repo import TaskRepo

mcp = FastMCP("tasker")


def get_repo() -> TaskRepo:
    tasker_dir = discover_tasker_dir()
    return TaskRepo(tasker_dir)


class MutationResult(BaseModel):
    id: str
    status: TaskStatus
    affected: list[str] = Field(
        default_factory=list,
        description=(
            "Subtask ids whose status changed as a side effect of force; "
            "omitted when nothing cascaded."
        ),
    )

    @model_serializer(mode="wrap")
    def _serialize(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        data: dict[str, Any] = handler(self)
        if not self.affected:
            data.pop("affected", None)
        return data

    @classmethod
    def from_task(cls, task: Task, affected: Iterable[Task] | None = None) -> Self:
        return cls(
            id=task.id,
            status=task.status,
            affected=[t.id for t in affected or []],
        )
