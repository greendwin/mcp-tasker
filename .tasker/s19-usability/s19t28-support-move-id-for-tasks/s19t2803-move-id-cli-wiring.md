---
id: s19t2803
slug: move-id-cli-wiring
status: done
---

# Move --id CLI wiring

## Goal

`tasker move <ref> --id <new-id>` works end-to-end: validates, renames, prints the right message, optionally opens the editor.

## Decisions & constraints

- `--id` joins the mutual-exclusivity group: exactly one of `--parent`/`--root`/`--delete`/`--id`. Single ref only (>1 ref → error). `--editor` allowed; `--delete` incompatible.
- Orchestration lives in `cmd_move_task` (CLI-side, mirroring how `--parent` is resolved before `repo.move_task`): normalize via `normalize_task_id` (strict), derive parent via `parse_task_ref`, resolve implied parent (None for root targets), run free + parent-exists checks via `repo.resolve_ref`, idempotency pre-check, then `repo.move_task(..., new_id=...)`.
- Free + parent-exists checks: parent must resolve (subtask targets); target must be a clean "not found" to be free; resolved-or-ambiguous = occupied. Loader's active→archive fallback covers archived.
- Idempotency: target == current id → no-op reusing "already in the requested location", skip uniqueness + move machinery.
- Message by outcome: root target → reuse `moved to root`; different parent → reuse `moved under {parent}`; same parent → new `renamed to {new_id}`. Shared `Renamed tasks:` block follows in all non-idempotent cases.
- `--id` option: `Optional[str]`, no short alias, no autocompletion (a completer would suggest occupied ids), conflict-resolution help text.
- Operates only on a loadable repo (hard dup-id collision states are out of scope).

## Edge cases

- `--id` with >1 ref → error; `--id` + `--parent`/`--root`/`--delete` → error.
- `--id` + `--editor` opens renamed task at its new id.
- target occupied → error; parent missing (subtask target) → error.
- idempotent target (current id); shorthand input flows through normalize.

## Key files

- `src/tasker/cli/_organize_commands.py`
- tests: `tests/test_organize_commands.py`

## Acceptance criteria

- `move s05t03 --id s05t07` renames in place and prints `renamed to s05t07`.
- `move s05t03 --id s07` prints `moved to root`; `move s05t03 --id s09t01` prints `moved under …`.
- `--id` with two refs, or combined with `--parent`/`--root`/`--delete`, errors; occupied target and missing-parent target both error.
