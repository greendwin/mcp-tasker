---
id: s13t1004
slug: rework-start-action-report-plus
status: pending
---

# Rework start: action report plus tree preview

## Goal

`start` emits the uniform action report (`Starting:` header, id-only bullets)
and then shows the status change highlighted in the task tree
(`print_parents_with_opened`) instead of re-printing the task text via
`print_task(preview=True)`.

## Decisions & constraints

- Preview change is deliberate scope (design review outcome): the user wants to
  see *where* the status changed in the tree, not reread the task body. The
  matching ADR 0004 accepted-deviation amendment (text preview: `edit` only)
  lands in the final slice.
- Reporter reuse + dedup by resolved id per the s13t1001 pattern.
- Outcomes: `(already started)` and `(restarted)` — restart of a done task is a
  deviation from the header's implied pending→in-progress action.
- Nonleaf handling unchanged: `_fail_starting_nonleaf_task` errors before any
  report.
- JSON contract unchanged (`task_refs` with task.ref); `.recent` unchanged.

## Edge cases

- Duplicate refs.
- Restarting a done task (`(restarted)`), starting an in-progress task
  (`(already started)`), plain start (no annotation) — all three in one
  invocation.
- Multiple tasks under different parents: one combined tree preview with all
  highlighted (print_parents_with_opened semantics), replacing N separate text
  previews.

## Key files

- `src/tasker/cli/_status_commands.py` — `cmd_start_task`
- `tests/test_start_review_commands.py`

## Acceptance criteria

- Human output: `Starting:` + bullets, then highlighted tree preview; no task
  text preview, no per-ref sentences.
- Duplicate-ref test: one bullet, one JSON entry, action applied once.
- Existing JSON-output tests pass unchanged.
- `uv run tox` passes (all environments).
