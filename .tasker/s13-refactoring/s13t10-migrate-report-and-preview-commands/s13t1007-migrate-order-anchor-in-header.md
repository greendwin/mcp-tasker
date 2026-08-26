---
id: s13t1007
slug: migrate-order-anchor-in-header
status: pending
---

# Migrate order: anchor in header, real bullets for rest

## Goal

`order` reports through the action report with the anchor in the header:
`Ordering after <anchor-id>:` (default), `Ordering at front:` (`--front`),
`Clearing order:` (`--clear`). Bullets cover every task the action touches —
the moved tasks and any `--rest`-swept siblings — replacing the freeform
"Grouping tasks after X: a, b" / "Moving tasks to the front: …" / "Reset
ordering for tasks:" echoes.

## Decisions & constraints

- **Anchor never gets a bullet** — it is the reference point, not a target, and
  an `(anchor)` bullet would annotate a non-deviation (against ADR 0004's
  deviation-only rule). It stays in the header and remains in `task_refs` JSON
  as today.
- **`--rest` extras get real bullets** — they receive the action itself (order
  materialized, possibly renamed), so bullets mirror their `task_refs` JSON
  entries and preview highlights. Rejected: collapsing them to a count (unlike
  descendant renames, these are top-level targets of the action).
- Cross-parent adoption renames (`_ensure_same_parent`) use the `(was <old-id>)`
  outcome pattern from the move slice; bullets and header use **final** ids
  (ADR 0004: order reports final ids; report after renames).
- Dedup by resolved id (e.g. a task listed twice, or listed and also swept by
  `--rest` — one bullet).
- The "specify at least one task" warning path stays as-is (no report).
- JSON contracts unchanged: `task_refs` (anchor + moved incl. rest for default;
  sorted set for `--front`), `renames`; `.recent` from final ids; preview
  unchanged.

## Edge cases

- `--rest` where swept siblings overlap explicitly listed tasks (dedup).
- Default mode where a moved task needs adoption under the anchor's parent
  (rename outcome on its bullet).
- `--clear` bullets: tasks listed in id order as today, no outcomes expected.
- `--front --rest` materializing a total order over many siblings.

## Key files

- `src/tasker/cli/_organize_commands.py` — `cmd_order_tasks`,
  `_reorder_tasks`, `_reorder_tasks_to_front`, `_clear_tasks_ordering`
- `tests/test_order_commands.py`, `tests/test_order_display.py`

## Acceptance criteria

- Each mode prints its header + bullets for all touched tasks (anchor excluded)
  with final ids; freeform echoes are gone.
- `--rest` bullets match the `task_refs` JSON entries one-to-one.
- Duplicate-ref test: one bullet, one JSON entry, action applied once.
- Existing JSON-output tests pass unchanged.
- `uv run tox` passes (all environments).
