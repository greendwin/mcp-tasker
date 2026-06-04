---
id: s27t02
slug: init-creates-tasker-noop-on
status: done
---

# `init` creates `.tasker/`; no-op on legacy

Make `tasker init` create `.tasker/` for new projects, and leave existing legacy `tasker/` projects untouched.

## Scope
- `init_tasker_dir(project_root)`: if a valid legacy `tasker/` exists at `project_root`, return that path unchanged. Otherwise create `.tasker/`.
- `--user` path still creates `tasker/` (covered by slice 4).

## Test first
- `tasker init` in empty dir → `.tasker/` created, `tasker/` absent.
- `tasker init` in dir with a pre-existing valid legacy `tasker/` → returns the legacy path, no `.tasker/` created, output mentions the legacy path.
- Re-running `tasker init` after a fresh init is idempotent on `.tasker/`.

## Demo
Fresh `tasker init` in an empty repo produces `.tasker/`.
