---
id: s13t1010
slug: migrate-new
status: pending
---

# Migrate new

## Goal

`new` reports through the action report — `Created:` header with one bullet
carrying the new task's id — before its existing highlighted preview, replacing
the one-sentence confirmation.

## Decisions & constraints

- Uniformity over brevity (design review outcome): every command parseable the
  same way; a one-bullet report is fine. Rejected: keeping the sentence
  confirmation (reintroduces a per-command special case).
- Singular `task_ref` JSON contract unchanged.
- Dedup rule is vacuous (no input refs) — no duplicate tests needed here.
- `--editor`, `.recent`, preview unchanged.

## Edge cases

- `--json-output`: report silent, `task_ref` payload identical to today.
- Bullet shows the id; the preview right below carries the title (ADR 0004:
  bullets are id-only).

## Key files

- `src/tasker/cli/_create_commands.py` — `cmd_new_task`
- `tests/test_create_commands.py`

## Acceptance criteria

- Human output: `Created:` + one bullet, then highlighted preview; no sentence
  confirmation.
- Existing JSON-output tests pass unchanged.
- `uv run tox` passes (all environments).
