---
id: s27t04
slug: userlevel-dir-stays-tasker-regression
status: done
---

# User-level dir stays `tasker/` (regression guard)

Pin that the `--user` flow is unaffected by the rename.

## Scope
- No production code change expected; slice exists to prevent regressions.

## Test first
- `tasker init --user` creates `tasker/` (not `.tasker/`) under the user base (XDG / LOCALAPPDATA, mocked via env).
- After `init --user`, `discover_tasker_dir` falls back to that user-level `tasker/` when no project dir is present.
