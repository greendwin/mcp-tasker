import os
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

import pytest
import typer._click.exceptions as _click_exceptions
from pyfakefs.fake_filesystem import FakeFilesystem

import tasker
from tasker.exceptions import TaskerError
from tasker.layout import ARCHIVE_DIR, DOT_TASKER_DIR, init_tasker_dir
from tasker.utils import OutputContext

# import helper fixture to make them available to all tests
from .helpers import get_task_file, run_editor, setup_task_edits  # noqa: F401


@pytest.fixture
def project_root() -> Path:
    proj_root = Path("/myproj")
    proj_root.mkdir()
    (proj_root / ".git").mkdir()
    init_tasker_dir(proj_root, DOT_TASKER_DIR)
    return proj_root


@pytest.fixture(autouse=True)
def setup_fake_fs(fs: FakeFilesystem, project_root: Path) -> None:
    fs.add_real_directory(Path(tasker.__file__).parent / "templates")
    os.chdir(project_root)


@contextmanager
def _bubbling_catching_errors(self: OutputContext) -> Generator[None, None, None]:
    # test harness: handle only TaskerError + Typer/Click exceptions exactly as
    # production does, and let every other (unexpected) exception propagate
    # straight to the test instead of being wrapped into a clean `Error:` exit.
    self._json_output_obj = {}
    try:
        yield
    except (
        _click_exceptions.ClickException,
        _click_exceptions.Exit,
        _click_exceptions.Abort,
    ):
        raise
    except TaskerError as ex:
        self._handle_error(ex, file_path=ex.file_path, json_output=ex.json_output)
    finally:
        if self.json_output:
            self._console.print_json(data=self._json_output_obj)


@pytest.fixture(autouse=True)
def bubble_unexpected_errors(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    # tests tagged `real_error_handling` exercise production's own wrapping
    if request.node.get_closest_marker("real_error_handling"):
        return
    monkeypatch.setattr(OutputContext, "catching_errors", _bubbling_catching_errors)


@pytest.fixture
def tasks_root(project_root: Path) -> Path:
    return init_tasker_dir(project_root, DOT_TASKER_DIR)


@pytest.fixture
def tasks_archive_root(tasks_root: Path) -> Path:
    return tasks_root / ARCHIVE_DIR
