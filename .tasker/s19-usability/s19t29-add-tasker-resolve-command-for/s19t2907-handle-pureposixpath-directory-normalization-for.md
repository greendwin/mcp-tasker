---
id: s19t2907
slug: handle-pureposixpath-directory-normalization-for
status: pending
---

# Handle PurePosixPath directory normalization for Windows compatibility

In `list_conflicted_files` (`src/tasker/git.py`), `PurePosixPath(directory).as_posix()` doesn't correctly normalize Windows backslash paths. On Windows, `Path(".tasker\\foo")` passed to `PurePosixPath()` treats backslashes as part of the filename rather than separators.

Fix: use `directory.as_posix()` or `str(directory).replace("\\", "/")` instead.

Low priority — tasker currently targets Linux only.
