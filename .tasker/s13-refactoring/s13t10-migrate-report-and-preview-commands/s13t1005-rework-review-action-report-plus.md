---
id: s13t1005
slug: rework-review-action-report-plus
status: pending
---

# Rework review: action report plus tree preview

## Goal

`review` mirrors the reworked `start` (s13t1004): uniform action report
(`Marking for review:` header, id-only bullets) followed by the highlighted
task-tree preview instead of the task-text preview.

## Decisions & constraints

- Twin of `start` — leaving it behind would recreate the inconsistency the
  migration removes. In-review tasks already render distinctly in tree lines
  (`[~] **review** Title`), so the tree shows the change clearly.
- Reporter reuse + dedup by resolved id per the s13t1001 pattern.
- Outcome: `(already in review)` no-op; plain transitions unannotated.
- Nonleaf handling unchanged: `_fail_reviewing_nonleaf_task` errors before any
  report.
- JSON contract unchanged (`task_refs`); `.recent` unchanged.

## Edge cases

- Duplicate refs.
- Mixed already-in-review + fresh transitions in one invocation.
- Multiple tasks → one combined highlighted tree preview.

## Key files

- `src/tasker/cli/_status_commands.py` — `cmd_review_task`
- `tests/test_start_review_commands.py`

## Acceptance criteria

- Human output: report + highlighted tree preview showing the `**review**`
  tag; no task-text preview, no per-ref sentences.
- Duplicate-ref test: one bullet, one JSON entry, action applied once.
- Existing JSON-output tests pass unchanged.
- `uv run tox` passes (all environments).
