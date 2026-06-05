from __future__ import annotations

from pathlib import Path

import pytest

from tasker import git
from tasker.cli import app
from tasker.git import ConflictedFile
from tasker.merge import MergeFileResult
from tests.helpers import assert_invoke


class TestResolveNoConflicts:
    def test_prints_no_conflicts_message(
        self,
        monkeypatch: pytest.MonkeyPatch,
        project_root: Path,
    ) -> None:
        monkeypatch.setattr(git, "list_conflicted_files", lambda *_a, **_kw: [])

        result = assert_invoke(app, ["resolve"])
        assert "No conflicts found" in result.output


class TestResolveSingleCleanMerge:
    def test_file_written_and_staged(
        self,
        monkeypatch: pytest.MonkeyPatch,
        project_root: Path,
    ) -> None:
        task_file = project_root / ".tasker" / "s01-foo.md"
        task_file.write_text("conflict markers here")

        cf = ConflictedFile(
            path=".tasker/s01-foo.md",
            base="base content",
            ours="ours content",
            theirs="theirs content",
        )
        monkeypatch.setattr(git, "list_conflicted_files", lambda *_a, **_kw: [cf])

        merged = MergeFileResult(content="merged content", has_conflicts=False)
        monkeypatch.setattr(
            "tasker.cli._resolve_commands.merge_task_file", lambda *_a, **_kw: merged
        )

        staged_paths: list[str] = []
        monkeypatch.setattr(
            git, "stage_file", lambda path, **_kw: staged_paths.append(str(path))
        )

        result = assert_invoke(app, ["resolve"])

        assert task_file.read_text() == "merged content"
        assert ".tasker/s01-foo.md" in staged_paths
        assert "1 resolved" in result.output


class TestResolveSingleConflictRemains:
    def test_file_written_but_not_staged(
        self,
        monkeypatch: pytest.MonkeyPatch,
        project_root: Path,
    ) -> None:
        task_file = project_root / ".tasker" / "s01-foo.md"
        task_file.write_text("conflict markers here")

        cf = ConflictedFile(
            path=".tasker/s01-foo.md",
            base="base content",
            ours="ours content",
            theirs="theirs content",
        )
        monkeypatch.setattr(git, "list_conflicted_files", lambda *_a, **_kw: [cf])

        merged = MergeFileResult(content="still has <<<<<<", has_conflicts=True)
        monkeypatch.setattr(
            "tasker.cli._resolve_commands.merge_task_file", lambda *_a, **_kw: merged
        )

        staged_paths: list[str] = []
        monkeypatch.setattr(
            git, "stage_file", lambda path, **_kw: staged_paths.append(str(path))
        )

        result = assert_invoke(app, ["resolve"])

        assert task_file.read_text() == "still has <<<<<<"
        assert staged_paths == []
        assert "1 conflict" in result.output.lower()


class TestResolveMultipleMixed:
    def test_correct_counts(
        self,
        monkeypatch: pytest.MonkeyPatch,
        project_root: Path,
    ) -> None:
        # Create two task files on disk
        task1 = project_root / ".tasker" / "s01-foo.md"
        task1.write_text("conflict 1")
        task2 = project_root / ".tasker" / "s02-bar.md"
        task2.write_text("conflict 2")

        cf1 = ConflictedFile(
            path=".tasker/s01-foo.md",
            base="b1",
            ours="o1",
            theirs="t1",
        )
        cf2 = ConflictedFile(
            path=".tasker/s02-bar.md",
            base="b2",
            ours="o2",
            theirs="t2",
        )
        monkeypatch.setattr(git, "list_conflicted_files", lambda *_a, **_kw: [cf1, cf2])

        call_count = 0

        def fake_merge(*args: object, **kwargs: object) -> MergeFileResult:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return MergeFileResult(content="clean", has_conflicts=False)
            return MergeFileResult(content="markers", has_conflicts=True)

        monkeypatch.setattr("tasker.cli._resolve_commands.merge_task_file", fake_merge)

        staged_paths: list[str] = []
        monkeypatch.setattr(
            git, "stage_file", lambda path, **_kw: staged_paths.append(str(path))
        )

        result = assert_invoke(app, ["resolve"])

        assert "1 resolved" in result.output
        assert "1 conflict" in result.output.lower()
        assert len(staged_paths) == 1


class TestResolveSkipsBrokenFile:
    def test_skips_with_warning(
        self,
        monkeypatch: pytest.MonkeyPatch,
        project_root: Path,
    ) -> None:
        # File with name that cannot be parsed as a task
        cf = ConflictedFile(
            path=".tasker/.gitignore",
            base="a",
            ours="b",
            theirs="c",
        )
        monkeypatch.setattr(git, "list_conflicted_files", lambda *_a, **_kw: [cf])

        result = assert_invoke(app, ["resolve"])
        assert "skip" in result.output.lower()
        assert "1 skipped" in result.output


class TestResolveSkipsMissingSide:
    def test_skips_when_ours_is_none(
        self,
        monkeypatch: pytest.MonkeyPatch,
        project_root: Path,
    ) -> None:
        task_file = project_root / ".tasker" / "s01-foo.md"
        task_file.write_text("conflict markers")

        cf = ConflictedFile(
            path=".tasker/s01-foo.md",
            base="base",
            ours=None,
            theirs="theirs",
        )
        monkeypatch.setattr(git, "list_conflicted_files", lambda *_a, **_kw: [cf])

        result = assert_invoke(app, ["resolve"])
        assert "skip" in result.output.lower()
        assert "1 skipped" in result.output


class TestResolveSkipsMergeError:
    def test_skips_when_merge_raises(
        self,
        monkeypatch: pytest.MonkeyPatch,
        project_root: Path,
    ) -> None:
        task_file = project_root / ".tasker" / "s01-foo.md"
        task_file.write_text("conflict markers")

        cf = ConflictedFile(
            path=".tasker/s01-foo.md",
            base="base",
            ours="ours",
            theirs="theirs",
        )
        monkeypatch.setattr(git, "list_conflicted_files", lambda *_a, **_kw: [cf])

        def exploding_merge(*_args: object, **_kwargs: object) -> MergeFileResult:
            raise ValueError("bad task content")

        monkeypatch.setattr(
            "tasker.cli._resolve_commands.merge_task_file", exploding_merge
        )

        result = assert_invoke(app, ["resolve"])
        assert "skip" in result.output.lower()
        assert "1 skipped" in result.output


class TestResolveExtendedTask:
    def test_extended_task_readme(
        self,
        monkeypatch: pytest.MonkeyPatch,
        project_root: Path,
    ) -> None:
        # Extended task: directory with README.md
        task_dir = project_root / ".tasker" / "s01-foo"
        task_dir.mkdir(parents=True)
        readme = task_dir / "README.md"
        readme.write_text("conflict markers")

        cf = ConflictedFile(
            path=".tasker/s01-foo/README.md",
            base="base",
            ours="ours",
            theirs="theirs",
        )
        monkeypatch.setattr(git, "list_conflicted_files", lambda *_a, **_kw: [cf])

        merged = MergeFileResult(content="merged ext", has_conflicts=False)
        monkeypatch.setattr(
            "tasker.cli._resolve_commands.merge_task_file", lambda *_a, **_kw: merged
        )

        staged_paths: list[str] = []
        monkeypatch.setattr(
            git, "stage_file", lambda path, **_kw: staged_paths.append(str(path))
        )

        result = assert_invoke(app, ["resolve"])

        assert readme.read_text() == "merged ext"
        assert ".tasker/s01-foo/README.md" in staged_paths
        assert "1 resolved" in result.output
