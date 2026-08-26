---
id: s13t1003
slug: action-report-for-reset
status: pending
---

# Action report for reset

## Goal

`reset` emits the uniform action report (`Resetting:` header, id-only bullets)
before its highlighted tree preview, replacing per-ref confirmation sentences.

## Decisions & constraints

- Apply the s13t1001 pattern: reporter reuse, dedup by resolved id, deviation-
  only outcomes.
- Outcomes: `(already pending)` no-op; `--force` cascade as
  `(forced N subtasks)` on the requested bullet only (reset forces non-pending
  subtasks back to pending).
- JSON contract unchanged (`task_refs`, `forced_task_ids`); `.recent` and
  preview unchanged.

## Edge cases

- Duplicate refs.
- Already-pending leaf mixed with a forced nonleaf in one invocation.
- Nonleaf without `--force` still errors via `_fail_resetting_nonleaf_task`
  before any report.

## Key files

- `src/tasker/cli/_status_commands.py` — `cmd_reset_task`
- `tests/test_reset_cancel_commands.py`

## Acceptance criteria

- Human output: `Resetting:` + bullets, then preview; no per-ref sentences.
- Duplicate-ref test: one bullet, one JSON entry, action applied once.
- Existing JSON-output tests pass unchanged.
- `uv run tox` passes (all environments).
