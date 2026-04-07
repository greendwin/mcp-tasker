---
id: s25t01
slug: support-developerreview-process
status: done
---

# Support developer-review process

Developer should not mark task as `done` but rather move it to `in-review`.
Parent tasks stay `in-progress` when a child is `in-review` (only leaf tasks can be `in-review`).

Reviewer either approves (`done`) or adds subtasks turning the task back to `pending`.

## Design decisions

- New `TaskStatus.IN_REVIEW` enum value, front matter: `status: in-review`
- `in-review` is open (like `in-progress`), not closed
- New CLI command: `tasker review <task-id>...` — same pattern as `start`, leaf-only
- Non-leaf tasks reject `review` with same error as `start`
- Parent auto-status: `in-review` child keeps parent `in-progress`
- Checkbox symbol: `[~]` (same as `in-progress`)
- Inline subtask rendering: `- [~] s01t01: **review** Task title`
- Parser: `[~]` + `**review**` prefix in title → `in-review`; strip tag from title on read, add on write
- CLI color: `cyan`
- CLI display: **review** label (cyan) before title in shared formatting function (used by `list` and `view`)
- `done` works on `in-review` tasks (acts as "approve"), `--force` closes them too — no changes to `done`
- MCP: add `review_task` tool with same pattern as `start_task`

## Subtasks

- [x] s25t0101: Add IN_REVIEW to TaskStatus enum and base_types
- [x] s25t0102: Update render module for in-review checkbox and tag
- [x] s25t0103: Update parser to read in-review from inline subtasks
- [x] s25t0104: Add review CLI command (leaf-only, same pattern as start)
- [x] s25t0105: Update CLI print utils for in-review color and label
- [x] s25t0106: Add review_task MCP tool
- [x] s25t0107: Update DESIGN.md with in-review status
