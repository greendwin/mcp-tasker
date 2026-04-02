import os
from pathlib import Path

import pytest
from pyfakefs.fake_filesystem import FakeFilesystem

import tasker

# import helper fixture to make them available to all tests
from .helpers import get_task_file, run_editor, setup_task_edits  # noqa: F401


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
