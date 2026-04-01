import os
from pathlib import Path
from typing import Protocol
from unittest import mock

import pytest
from pyfakefs.fake_filesystem import FakeFilesystem

import tasker
from tasker.cli import _task_commands


@pytest.fixture
def project_root() -> Path:
    proj_root = Path("/myproj")
    proj_root.mkdir()
    return proj_root


@pytest.fixture(autouse=True)
def setup_fake_fs(fs: FakeFilesystem, project_root: Path) -> None:
    fs.add_real_directory(Path(tasker.__file__).parent / "templates")
    os.chdir(project_root)


@pytest.fixture
def tasks_root(project_root: Path) -> Path:
    root_dir = project_root / "tasker"
    root_dir.mkdir(parents=True, exist_ok=True)
    return root_dir


@pytest.fixture
def tasks_archive_root(tasks_root: Path) -> Path:
    root_dir = tasks_root / "archive"
    root_dir.mkdir(parents=True, exist_ok=True)
    return root_dir


class GetTaskFile(Protocol):
    def __call__(self, task_id: str) -> Path: ...


@pytest.fixture
def get_task_file(tasks_root: Path) -> GetTaskFile:
    def callback(task_id: str) -> Path:
        path = next(tasks_root.glob(f"{task_id}-*.md"), None)
        assert path is not None, f"No task file found for {task_id!r} in {tasks_root}"
        return path

    return callback


@pytest.fixture(autouse=True)
def open_in_editor(monkeypatch: pytest.MonkeyPatch) -> mock.Mock:
    # always mock `open_in_editor` to avoid process spawn
    m = mock.Mock(return_value=None)
    monkeypatch.setattr(_task_commands, "open_in_editor", m)
    return m
