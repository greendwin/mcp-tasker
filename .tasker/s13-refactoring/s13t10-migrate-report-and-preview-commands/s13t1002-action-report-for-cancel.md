---
id: s13t1002
slug: action-report-for-cancel
status: pending
---

# Action report for cancel

## Goal

`cancel` emits the uniform action report (`Cancelling:` header, id-only
bullets) before its highlighted tree preview, replacing per-ref confirmation
sentences.

## Decisions & constraints

- Apply the pattern established by the `done` slice (s13t1001) verbatim:
  reporter reuse, dedup by resolved id (one bullet / one JSON entry / one
  application), deviation-only outcomes.
- Outcomes: `(already cancelled)` no-op; `--force` cascade as
  `(forced N open subtasks)` on the requested bullet only.
- JSON contract unchanged (`task_refs` with task.ref, `forced_task_ids`);
  `.recent`, `save_closed_refs`, preview unchanged.

## Edge cases

- Duplicate refs (id vs id-slug forms of the same task).
- Mixed invocation: one already-cancelled, one forced nonleaf.
- Nonleaf without `--force` still errors via `_fail_cancelling_nonleaf_task`
  before any report is printed.

## Key files

- `src/tasker/cli/_status_commands.py` — `cmd_cancel_task`
- `tests/test_reset_cancel_commands.py`

## Acceptance criteria

- Human output: `Cancelling:` + bullets, then preview; no per-ref sentences.
- Duplicate-ref test: one bullet, one JSON entry, action applied once.
- Existing JSON-output tests pass unchanged.
- `uv run tox` passes (all environments).
