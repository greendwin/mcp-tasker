from pathlib import Path

import pytest

import tasker.repo as repo_mod
from tasker.cli import app

from .helpers import assert_invoke, create_task


def test_unexpected_exception_bubbles(monkeypatch: pytest.MonkeyPatch) -> None:
    create_task("Story")

    def _boom(self: object, *, archived: bool = False) -> list[Path]:
        raise RuntimeError("boom-unexpected")

    monkeypatch.setattr(repo_mod.TaskRepo, "list_root_tasks", _boom)

    # an unexpected error surfaces to the test, not swallowed into a clean exit 1
    with pytest.raises(RuntimeError, match="boom-unexpected"):
        assert_invoke(app, ["list"])
