---
id: s13t1009
slug: migrate-unarchive
status: pending
---

# Migrate unarchive

## Goal

`unarchive` emits an `Unarchiving:` action report (id-only bullets, dedup,
deviation-only outcomes) before its existing highlighted tree preview,
replacing per-ref confirmation sentences.

## Decisions & constraints

- Straight application of the standard pattern (s13t1001): reporter reuse,
  dedup by resolved id, outcome `(already unarchived)` for no-ops.
- `.recent` **is** updated (unlike archive — unarchive brings a story back
  into scope, per ADR 0004's deviation note).
- Root-only validation unchanged; errors raise before any report.
- JSON contract unchanged: `task_refs`, `already`.

## Edge cases

- Duplicate refs.
- Mixed already-unarchived + freshly unarchived in one invocation.
- Preview shows the restored story highlighted in the active tree.

## Key files

- `src/tasker/cli/_organize_commands.py` — `cmd_unarchive_task`
- `tests/test_archive_commands.py`

## Acceptance criteria

- Human output: `Unarchiving:` + bullets, then highlighted preview; no per-ref
  sentences.
- Duplicate-ref test: one bullet, one JSON entry, action applied once.
- Existing JSON-output tests pass unchanged.
- `uv run tox` passes (all environments).
