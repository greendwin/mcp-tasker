---
id: s13t1011
slug: migrate-add-finalize-adr-0004
status: pending
---

# Migrate add; finalize ADR 0004

## Goal

`add` reports through the action report — anchor-in-header pattern,
`Adding under <parent-id>:` with one bullet carrying the child's id — before
its existing highlighted preview. With that, every in-scope command speaks the
format, so ADR 0004 is updated to its final state.

## Decisions & constraints

- Parent in the header mirrors the `order` anchor decision: the parent is the
  reference point, the child is the acted-on task.
- Singular `task_ref` JSON contract unchanged; `parent_ref` context if present
  stays; auto-unarchive of the parent, `--editor`, `.recent`, preview
  unchanged.
- **ADR 0004 final amendments** (lands here so the adoption claim is true the
  moment it is written):
  - Adopter note: the action-report format is adopted by all report-and-preview
    commands (`todo`, `untodo`, `done`, `cancel`, `reset`, `start`, `review`,
    `move`, `order`, `archive`, `unarchive`, `new`, `add`).
  - Accepted deviations amended: task-text preview is now `edit` only
    (`start`/`review` moved to the tree preview); `archive` still skips
    `.recent` but now shows the remaining-roots overview with dimmed archived
    stories; `add-many` unchanged (bulk primitive, no per-task preview).
  - Note `move --id` self-move now complies with contracts 1 and 3.
- `add-many` stays out of scope.

## Edge cases

- `--json-output`: report silent, payload identical.
- Adding under an archived parent (auto-unarchive) — report still prints after
  the unarchive side effect.

## Key files

- `src/tasker/cli/_create_commands.py` — `cmd_add_task`
- `docs/adr/0004-commands-speak-json-recent-and-preview.md`
- `tests/test_create_commands.py`

## Acceptance criteria

- Human output: `Adding under <parent>:` + one bullet, then highlighted
  preview; no sentence confirmation.
- ADR 0004 reflects full adoption and the amended deviations.
- Existing JSON-output tests pass unchanged.
- `uv run tox` passes (all environments).
