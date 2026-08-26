---
id: s13t1001
slug: action-report-for-done
status: pending
---

# Action report for done

## Goal

`done` (and its `--reviewed` mode) emits the uniform action report before its
highlighted tree preview: `Finishing:` header, one bullet per requested ref,
deviation-only outcomes. Per-ref confirmation sentences (`Task X finished`) are
gone. This is the s13t10 tracer slice — it establishes the pattern the other
status commands copy.

## Decisions & constraints

- Reuse `ActionReportConfig` / `print_action_report` from `_print_utils.py` —
  no new rendering mode (ADR 0004).
- **Dedup**: requested refs dedupe by resolved task id before processing,
  first-occurrence order — one bullet, one `task_refs` JSON entry, one
  application; a duplicate is never annotated.
- Outcomes: `(already done)` for a no-op; `--force` cascade collapses to a
  count on the requested bullet, e.g. `(forced 3 open subtasks)`. Rejected: a
  bullet per forced subtask — the enumeration already exists in preview
  highlights and `forced_task_ids` JSON.
- JSON contract unchanged: `task_refs` (task.ref values, as today) and
  `forced_task_ids` keep their shape; reporter is print-only and silent under
  `--json-output`. Emit context via `console.append_context` like `todo` does.
- `--reviewed`-swept tasks are requested refs in effect: they get bullets and
  `task_refs` entries as today.
- `.recent`, `save_closed_refs`, preview (`print_parents_with_opened`,
  forced tasks highlighted) all unchanged.

## Edge cases

- Duplicate refs where one is an id and one an id-slug ref to the same task.
- `--force` on a nonleaf plus `(already done)` mixing in one invocation.
- `--reviewed` with an explicitly listed task that is also in review (already
  deduped today via mentioned_tasks — keep one bullet).
- Empty resolved list with `--reviewed` → existing "No tasks to close." path
  unchanged (no empty report header).

## Key files

- `src/tasker/cli/_status_commands.py` — `cmd_done_task`
- `src/tasker/cli/_print_utils.py` — reporter (reuse)
- `tests/test_done_commands.py`, `tests/test_action_report.py`

## Acceptance criteria

- Human output: `Finishing:` + id-only bullets, then preview; no per-ref
  sentences.
- Duplicate-ref test mirroring todo/untodo: one bullet, one JSON entry, action
  applied once.
- Existing JSON-output tests pass unchanged.
- `uv run tox` passes (all environments).
