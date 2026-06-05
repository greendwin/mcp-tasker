---
id: s19t2905
slug: cli-command-and-endtoend-integration
status: pending
---

# CLI command and end-to-end integration

## Goal

`tasker resolve` command that ties git plumbing and merge logic together, writes results, stages fully-resolved files, and prints colored output.

## Decisions & constraints

- No arguments, processes all `.tasker/` conflicts. Fully resolved → `git add`. Partial → write with markers, don't stage.
- Rich-colored per-file status (green "resolved", yellow "conflicts") + colored summary.
- Ignore non-tasker conflicts but mention count in summary.
- Must parse file paths to derive `task_id`, `slug`, `extended` for `parse_task()` — uses existing `detect_task_type` or equivalent on the path.
- Serialize via `render_task()` for auto-resolved parts; conflict markers already injected by merge module.

## Edge cases

- No conflicts at all → "No merge conflicts found"
- Conflicts only outside `.tasker/` → "No conflicts in .tasker/"
- Not a git repo → error
- Non-task files under `.tasker/` conflicting (`.gitignore`) → skip or pass through

## Key files

- `src/tasker/cli/_resolve_commands.py` (new), `src/tasker/cli/__init__.py`, `src/tasker/cli/_common.py`

## Acceptance criteria

- Running `tasker resolve` during a merge with `.tasker/` conflicts produces resolved files
- Fully resolved files are staged
- Partially resolved files have standard conflict markers and are NOT staged
- Output shows per-file status with colors and summary
- Clean exit when no conflicts found
