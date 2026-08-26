---
id: s13t1006
slug: migrate-move-renames-as-bullet
status: pending
---

# Migrate move: renames as bullet outcomes

## Goal

`move` reports through the action report with a mode-specific header —
`Moving under <parent>:` / `Moving to root:` / `Renaming:` (`--id`) /
`Deleting:` (`--delete`) — and bullets carrying **final** ids, annotated with
the rename mapping when the id changed. The human `Renamed tasks:` listing
disappears; per-ref confirmation prose disappears; the `--id` self-move no-op
joins the normal flow.

## Decisions & constraints

- Bullet outcomes: `(was <old-id>)` for a renamed requested ref, extended with
  a descendant count when children shifted — `(was s01t03, renamed 4 subtasks)`.
  Rename-mapping-as-outcome is ADR 0004's own example; descendant renames
  collapse to a count like forced cascades (design review outcome). Rejected:
  keeping the full `Renamed tasks:` human listing (duplicates requested refs)
  and per-descendant bullets (noise).
- `renames` JSON stays **complete** — every rename including descendants, via
  context emission decoupled from the removed human block.
- `--id` self-move (target == current id): fold the early return into the
  normal flow — bullet `(already in place)`, then `.recent` update and
  highlighted preview like the other no-op path (empty renames), fixing its
  latent ADR 0004 contract-1/3 gap. This is the one sanctioned behavior change.
- Other no-op path (empty renames) gets the same `(already in place)` outcome.
- Dedup by resolved id per the standard rule.
- `task_refs` JSON, `parent_ref` context, auto-unarchive, `--editor`, preview
  all unchanged.

## Edge cases

- Final-id rule: bullets must show post-move ids even though the user typed
  pre-move refs (ADR 0004 contract 3).
- Multi-task move where some are no-ops and some rename.
- `--delete` mode: bullets are the deleted ids, no rename outcomes.
- `--id` rename within the same parent (header `Renaming:`, outcome
  `(was <old-id>)`).
- Duplicate refs to the same task.
- Extended tasks whose whole subtree renames (count covers all descendants).

## Key files

- `src/tasker/cli/_organize_commands.py` — `cmd_move_task`,
  `_print_renamed_tasks` (removal/repurposing), `_resolve_id_ref_param`
- `tests/test_move_commands.py`, `tests/test_move_flags_commands.py`

## Acceptance criteria

- Each mode prints its header + final-id bullets; no `Renamed tasks:` block, no
  per-ref sentences.
- `renames` JSON still lists every rename including descendants.
- `--id` self-move now reports, updates `.recent`, and previews.
- Duplicate-ref test: one bullet, one JSON entry, action applied once.
- Existing JSON-output tests pass unchanged (except the self-move path's
  documented additions).
- `uv run tox` passes (all environments).
