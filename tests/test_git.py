from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest

from tasker import git


class TestLsFilesUnmerged:
    """Tests for the parsing logic inside _ls_files_unmerged."""

    @staticmethod
    def _parse(
        monkeypatch: pytest.MonkeyPatch, output: str, directory: str
    ) -> dict[str, list[str | None]]:
        monkeypatch.setattr(git, "_run_git", lambda *_a, **_kw: output)
        return git._ls_files_unmerged(None, directory)

    def test_groups_stages_by_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        output = (
            "100644 abc123 1\t.tasker/s01-foo.md\n"
            "100644 def456 2\t.tasker/s01-foo.md\n"
            "100644 789abc 3\t.tasker/s01-foo.md\n"
        )
        result = self._parse(monkeypatch, output, ".tasker")
        assert result == {
            ".tasker/s01-foo.md": ["abc123", "def456", "789abc"],
        }

    def test_filters_to_directory(self, monkeypatch: pytest.MonkeyPatch) -> None:
        output = (
            "100644 abc123 1\t.tasker/s01-foo.md\n"
            "100644 def456 2\t.tasker/s01-foo.md\n"
            "100644 111111 1\tother/file.md\n"
            "100644 222222 2\tother/file.md\n"
        )
        result = self._parse(monkeypatch, output, ".tasker")
        assert ".tasker/s01-foo.md" in result
        assert "other/file.md" not in result

    def test_missing_stages(self, monkeypatch: pytest.MonkeyPatch) -> None:
        output = (
            "100644 def456 2\t.tasker/s01-foo.md\n"
            "100644 789abc 3\t.tasker/s01-foo.md\n"
        )
        result = self._parse(monkeypatch, output, ".tasker")
        assert result == {
            ".tasker/s01-foo.md": [None, "def456", "789abc"],
        }

    def test_empty_output(self, monkeypatch: pytest.MonkeyPatch) -> None:
        result = self._parse(monkeypatch, "", ".tasker")
        assert result == {}

    def test_multiple_files(self, monkeypatch: pytest.MonkeyPatch) -> None:
        output = (
            "100644 aaa111 1\t.tasker/s01-foo.md\n"
            "100644 bbb222 2\t.tasker/s01-foo.md\n"
            "100644 ccc333 1\t.tasker/s02-bar.md\n"
            "100644 ddd444 3\t.tasker/s02-bar.md\n"
        )
        result = self._parse(monkeypatch, output, ".tasker")
        assert result == {
            ".tasker/s01-foo.md": ["aaa111", "bbb222", None],
            ".tasker/s02-bar.md": ["ccc333", None, "ddd444"],
        }

    def test_trailing_slash_directory(self, monkeypatch: pytest.MonkeyPatch) -> None:
        output = "100644 abc123 1\t.tasker/s01-foo.md\n"
        result = self._parse(monkeypatch, output, ".tasker/")
        assert ".tasker/s01-foo.md" in result

    def test_skips_malformed_lines_without_tab(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        output = (
            "100644 abc123 1\t.tasker/s01-foo.md\n"
            "this line has no tab character\n"
            "100644 def456 2\t.tasker/s01-foo.md\n"
        )
        result = self._parse(monkeypatch, output, ".tasker")
        assert result == {
            ".tasker/s01-foo.md": ["abc123", "def456", None],
        }

    def test_skips_malformed_meta_with_tab(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        output = (
            "100644 abc123 1\t.tasker/s01-foo.md\n"
            "badmeta\tsome/path\n"
            "100644 def456 2\t.tasker/s01-foo.md\n"
        )
        result = self._parse(monkeypatch, output, ".tasker")
        assert result == {
            ".tasker/s01-foo.md": ["abc123", "def456", None],
        }

    def test_backslash_path_normalized_to_forward_slashes(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        output = (
            "100644 abc123 1\t.tasker/s01-foo.md\n"
            "100644 def456 2\t.tasker/s01-foo.md\n"
        )
        result = self._parse(monkeypatch, output, ".tasker\\s01-foo")
        assert result == {}  # backslash dir shouldn't match nested path

        # But the normalized form should filter correctly for the parent dir
        result2 = self._parse(monkeypatch, output, ".tasker")
        assert ".tasker/s01-foo.md" in result2

    def test_backslash_directory_matches_files(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        output = (
            "100644 aaa 1\t.tasker/sub/file.md\n" "100644 bbb 2\t.tasker/sub/file.md\n"
        )
        result = self._parse(monkeypatch, output, ".tasker\\sub")
        assert ".tasker/sub/file.md" in result

    def test_nested_subdirectory(self, monkeypatch: pytest.MonkeyPatch) -> None:
        output = (
            "100644 aaa 1\t.tasker/s01-foo/README.md\n"
            "100644 bbb 2\t.tasker/s01-foo/README.md\n"
            "100644 ccc 1\t.tasker/s02-bar.md\n"
        )
        result = self._parse(monkeypatch, output, ".tasker/s01-foo")
        assert ".tasker/s01-foo/README.md" in result
        assert ".tasker/s02-bar.md" not in result


class TestListConflictedFiles:
    def test_returns_conflicted_files_with_content(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        ls_output = (
            "100644 abc123 1\t.tasker/s01-foo.md\n"
            "100644 def456 2\t.tasker/s01-foo.md\n"
            "100644 789abc 3\t.tasker/s01-foo.md\n"
        )

        def fake_run_git(*args: str, **_kw: Any) -> str:
            if args[0] == "ls-files":
                return ls_output
            if args[0] == "cat-file":
                return f"content-of-{args[2]}"
            raise AssertionError(f"unexpected git call: {args}")

        monkeypatch.setattr(git, "_run_git", fake_run_git)

        result = git.list_conflicted_files(Path(".tasker"))
        assert len(result) == 1
        cf = result[0]
        assert cf.path == ".tasker/s01-foo.md"
        assert cf.base == "content-of-abc123"
        assert cf.ours == "content-of-def456"
        assert cf.theirs == "content-of-789abc"

    def test_missing_base_stage(self, monkeypatch: pytest.MonkeyPatch) -> None:
        ls_output = (
            "100644 def456 2\t.tasker/s01-foo.md\n"
            "100644 789abc 3\t.tasker/s01-foo.md\n"
        )

        def fake_run_git(*args: str, **_kw: Any) -> str:
            if args[0] == "ls-files":
                return ls_output
            if args[0] == "cat-file":
                return f"content-of-{args[2]}"
            raise AssertionError(f"unexpected git call: {args}")

        monkeypatch.setattr(git, "_run_git", fake_run_git)

        result = git.list_conflicted_files(Path(".tasker"))
        assert len(result) == 1
        cf = result[0]
        assert cf.base is None
        assert cf.ours == "content-of-def456"
        assert cf.theirs == "content-of-789abc"

    def test_empty_when_no_conflicts(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(git, "_run_git", lambda *_args, **_kw: "")
        result = git.list_conflicted_files(Path(".tasker"))
        assert result == []

    def test_multiple_conflicted_files(self, monkeypatch: pytest.MonkeyPatch) -> None:
        ls_output = (
            "100644 aaa 1\t.tasker/s01-foo.md\n"
            "100644 bbb 2\t.tasker/s01-foo.md\n"
            "100644 ccc 3\t.tasker/s01-foo.md\n"
            "100644 ddd 2\t.tasker/s02-bar.md\n"
            "100644 eee 3\t.tasker/s02-bar.md\n"
        )

        def fake_run_git(*args: str, **_kw: Any) -> str:
            if args[0] == "ls-files":
                return ls_output
            if args[0] == "cat-file":
                return f"content-of-{args[2]}"
            raise AssertionError(f"unexpected git call: {args}")

        monkeypatch.setattr(git, "_run_git", fake_run_git)

        result = git.list_conflicted_files(Path(".tasker"))
        assert len(result) == 2
        by_path = {cf.path: cf for cf in result}

        foo = by_path[".tasker/s01-foo.md"]
        assert foo.base == "content-of-aaa"
        assert foo.ours == "content-of-bbb"
        assert foo.theirs == "content-of-ccc"

        bar = by_path[".tasker/s02-bar.md"]
        assert bar.base is None
        assert bar.ours == "content-of-ddd"
        assert bar.theirs == "content-of-eee"

    def test_dot_directory_matches_all_files(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        ls_output = (
            "100644 aaa 1\t.tasker/s01-foo.md\n"
            "100644 bbb 2\t.tasker/s01-foo.md\n"
            "100644 ccc 1\tother/file.md\n"
            "100644 ddd 2\tother/file.md\n"
        )

        def fake_run_git(*args: str, **_kw: Any) -> str:
            if args[0] == "ls-files":
                return ls_output
            if args[0] == "cat-file":
                return f"content-of-{args[2]}"
            raise AssertionError(f"unexpected git call: {args}")

        monkeypatch.setattr(git, "_run_git", fake_run_git)

        result = git.list_conflicted_files(Path("."))
        assert len(result) == 2
        paths = {cf.path for cf in result}
        assert paths == {".tasker/s01-foo.md", "other/file.md"}

    def test_absolute_directory_without_repo_root_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(git, "_run_git", lambda *_a, **_kw: "")
        with pytest.raises(ValueError, match="repo_root"):
            git.list_conflicted_files(Path("/work/.tasker"))

    def test_absolute_directory_not_under_repo_root_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(git, "_run_git", lambda *_a, **_kw: "")
        with pytest.raises(ValueError):
            git.list_conflicted_files(Path("/tmp/other"), repo_root=Path("/work"))

    def test_absolute_directory_is_relativized(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        ls_output = (
            "100644 abc123 1\t.tasker/s01-foo.md\n"
            "100644 def456 2\t.tasker/s01-foo.md\n"
        )

        def fake_run_git(*args: str, **_kw: Any) -> str:
            if args[0] == "ls-files":
                return ls_output
            if args[0] == "cat-file":
                return f"content-of-{args[2]}"
            raise AssertionError(f"unexpected git call: {args}")

        monkeypatch.setattr(git, "_run_git", fake_run_git)

        repo_root = Path("/work/repo")
        result = git.list_conflicted_files(repo_root / ".tasker", repo_root=repo_root)
        assert len(result) == 1
        assert result[0].path == ".tasker/s01-foo.md"

    def test_backslash_directory_normalizes_and_matches(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify that backslash paths are normalized before filtering."""
        ls_output = (
            "100644 aaa 1\t.tasker/sub/file.md\n" "100644 bbb 2\t.tasker/sub/file.md\n"
        )

        def fake_run_git(*args: str, **_kw: Any) -> str:
            if args[0] == "ls-files":
                return ls_output
            if args[0] == "cat-file":
                return f"content-of-{args[2]}"
            raise AssertionError(f"unexpected git call: {args}")

        monkeypatch.setattr(git, "_run_git", fake_run_git)

        class BackslashPath:
            def is_absolute(self) -> bool:
                return False

            def __str__(self) -> str:
                return ".tasker\\sub"

        result = git.list_conflicted_files(cast(Path, BackslashPath()))
        assert len(result) == 1
        assert result[0].path == ".tasker/sub/file.md"

    def test_content_retrieval_calls(self, monkeypatch: pytest.MonkeyPatch) -> None:
        ls_output = "100644 aaa 1\t.tasker/f.md\n" "100644 bbb 2\t.tasker/f.md\n"
        calls: list[tuple[str, ...]] = []

        def fake_run_git(*args: str, **_kw: Any) -> str:
            calls.append(args)
            if args[0] == "ls-files":
                return ls_output
            if args[0] == "cat-file":
                return "blob-content"
            raise AssertionError(f"unexpected git call: {args}")

        monkeypatch.setattr(git, "_run_git", fake_run_git)
        git.list_conflicted_files(Path(".tasker"))

        cat_calls = [c for c in calls if c[0] == "cat-file"]
        assert ("cat-file", "-p", "aaa") in cat_calls
        assert ("cat-file", "-p", "bbb") in cat_calls
        assert len(cat_calls) == 2


class TestStageFile:
    def test_calls_git_add_with_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[tuple[str, ...]] = []

        def fake_run_git(*args: str, **_kw: Any) -> str:
            calls.append(args)
            return ""

        monkeypatch.setattr(git, "_run_git", fake_run_git)
        git.stage_file(Path(".tasker/s01-foo.md"))

        assert len(calls) == 1
        assert calls[0] == ("add", "--", ".tasker/s01-foo.md")

    def test_calls_git_add_with_string(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[tuple[str, ...]] = []

        def fake_run_git(*args: str, **_kw: Any) -> str:
            calls.append(args)
            return ""

        monkeypatch.setattr(git, "_run_git", fake_run_git)
        git.stage_file(".tasker/s01-foo.md")

        assert len(calls) == 1
        assert calls[0] == ("add", "--", ".tasker/s01-foo.md")
