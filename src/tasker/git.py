from __future__ import annotations

import subprocess
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias


@dataclass
class ConflictedFile:
    path: str  # repo-relative path
    base: str | None  # stage 1 (None if absent)
    ours: str | None  # stage 2
    theirs: str | None  # stage 3


def list_conflicted_files(
    directory: Path, *, repo_root: Path | None = None
) -> list[ConflictedFile]:
    if directory.is_absolute():
        if repo_root is None:
            raise ValueError("repo_root is required when directory is an absolute path")

        directory = directory.relative_to(repo_root)

    parsed = _ls_files_unmerged(repo_root, str(directory))

    conflicts = []
    for path, stages in parsed.items():
        cf = ConflictedFile(
            path=path,
            base=_read_blob(stages[0], cwd=repo_root),
            ours=_read_blob(stages[1], cwd=repo_root),
            theirs=_read_blob(stages[2], cwd=repo_root),
        )
        conflicts.append(cf)

    return conflicts


def _run_git(*args: str, cwd: Path | None = None) -> str:
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        check=True,
        cwd=cwd,
    )
    return result.stdout


_PathStageBlobs: TypeAlias = dict[str, list[str | None]]


def _ls_files_unmerged(repo_root: Path | None, directory: str) -> _PathStageBlobs:
    output = _run_git("ls-files", "--unmerged", cwd=repo_root)

    directory = directory.replace("\\", "/")
    match_all = directory in (".", "")
    prefix = directory.rstrip("/") + "/"

    # {path: {stage_num: blob_hash}} for paths under *directory*.
    result: _PathStageBlobs = defaultdict(lambda: [None, None, None])
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue

        # Format: "<mode> <hash> <stage>\t<path>"
        if "\t" not in line:
            continue

        meta, tab_path = line.split("\t", 1)
        parts = meta.split()
        if len(parts) < 3:
            continue

        blob_hash = parts[1]
        stage = int(parts[2]) - 1  # convert to zero-based

        if not match_all and not tab_path.startswith(prefix):
            continue

        result[tab_path][stage] = blob_hash

    return result


def _read_blob(blob_hash: str | None, *, cwd: Path | None = None) -> str | None:
    if blob_hash is None:
        return None

    return _run_git("cat-file", "-p", blob_hash, cwd=cwd)


def stage_file(path: str | Path, *, repo_root: Path | None = None) -> None:
    _run_git("add", "--", str(path), cwd=repo_root)
