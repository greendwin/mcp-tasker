---
id: s26t17
slug: parent-task-keep-in-progress
status: done
---

# Parent task keep in-progress after moving away all subtasks by --id

## Context

When a task that has subtasks (a "story"/container) loses its last subtask, its status is never recomputed and it keeps a stale, auto-derived status (typically `in-progress`). The reported trigger is moving a subtask away with `--id`, but the same defect reproduces via `--parent` and `--delete`. Goal: an emptied story should settle to `done`, and the whole ancestor chain should recompute so genuinely-complete ancestors cascade to `done` as well.

## Root cause

`get_status_from_subtasks` returns `task.status` unchanged when a task has no non-deleted subtasks. That preserve-branch is correct for a moved leaf (must keep its status) and for leaves loaded from disk, but it also leaves an emptied story stalled on its old derived status.

## Decisions

- **Fix the shared root cause, not just `--id`** — the defect is general; `--id`, `--parent`, and `--delete` all empty a parent through the same path. A narrow `--id`-only fix would leave two equivalent bugs live and split one behavior across code paths.
- **An emptied story settles to `done`** — a story with no outstanding work is complete; this is the vacuous case of the existing "all subtasks closed → done" rule. *Rejected: reset to `pending` — a parent's status only ever projected its (now-absent) children, but "fresh leaf → pending" was judged less natural than "container with no work left → finished."*
- **Uniform, regardless of departed children** — always `done`, whether the removed children were pending, in-progress, or closed. Self-corrects: adding a new subtask re-derives the status. *Rejected: conditional (done only if a child had been closed, else pending) — adds provenance tracking for a rare reorg case; the "reorg empties a story → done" edge is accepted as rare and reversible.*
- **Opt-in at the remove-last-child site, never global** — the `get_status_from_subtasks` empty-branch must stay preserve-by-default: it also serves the moved leaf (must keep its status) and on-load leaves (would be corrupted to `done` otherwise). At `_detach_from_parent` (covers `--id`/`--parent`) and `delete_task_impl` (covers `--delete`), once the child is removed, if the immediate parent has no non-deleted subtasks, set `parent.status = DONE` *before* calling `update_parents_status`. The existing preserve-branch then keeps that `DONE` and still applies the extended→inline downgrade. *Rejected: threading a `finish_if_empty` flag through `update_parents_status` → `update_task_status_and_flags` → `get_status_from_subtasks` — deriving `done` from an empty list is semantically odd and would need guarding at every caller anyway.*
- **Delete resolves its own immediate parent** — `delete_task_impl` doesn't hold the parent object; resolve it via `parse_task_ref(task.ref).parent_id`, and guard the root case (a root has no parent to update). Only the immediate parent can be emptied — ancestors still contain the intervening node.
- **Ancestor cascade comes for free via ordering** — set the immediate parent `DONE` first, then the existing full ancestor walk in `update_parents_status` re-derives each ancestor from its children: an ancestor turns `done` only when all its children are closed, and correctly stays `in-progress` if any sibling is still open. No special cascade logic, no false cascades.

## Edge cases

- **Moved leaf must not flip to `done`** — moving an in-progress leaf to a new parent keeps it `in-progress` (`get_status_from_subtasks` empty-branch preserves). This is the reason the fix is not global.
- **On-load leaves must not flip** — `_task_loader` calls `update_task_status_and_flags` on load; a genuine leaf stored as `in-progress` must stay so.
- **Root story emptied** — a root story stays file-based (no inline downgrade) but still settles to `done`.
- **Emptied non-root story with no description** — still downgrades extended→inline as today, now rendered as a closed (`- [x]`) inline bullet.
- **Departed children all-open (pending/in-progress)** — still `done` (uniform rule), even though nothing was ever completed.
- **Cascade must not over-fire** — a grandparent with a still-open sibling stays `in-progress`; only genuinely all-closed ancestors become `done`.
- **Idempotent / same-parent moves** — early-return paths in `move_task_impl` must be unaffected (no detach happens, so no spurious `done`).

## Key files

- `src/tasker/repo/_move_task.py` — `_detach_from_parent` (move: `--id`/`--parent`) and `delete_task_impl` (`--delete`); add the "immediate parent emptied → set `DONE` before `update_parents_status`" logic, with a small shared helper.
- `src/tasker/repo/_utils.py` — `get_status_from_subtasks` / `update_parents_status` stay as-is (empty→preserve is relied upon); reference only.
- `tests/test_organize_commands.py` — update the stale assertion in `test_move_all_subtasks_downgrades_parent_to_inline`; add the regressions below.

## Acceptance criteria

- Moving a story's only **in-progress** child away via `--id` leaves the source story `done` (repro from the bug report).
- Same via `--parent` leaves the source story `done`.
- Same via `--delete` leaves the source story `done`.
- A two-level story where emptying the inner story flips both it and its now-all-closed ancestor to `done` (cascade).
- A moved in-progress **leaf** keeps `in-progress` at its new location (`test_moved_task_preserves_status` still passes).
- An ancestor with an open sibling stays `in-progress` (no false cascade).
- `test_move_all_subtasks_downgrades_parent_to_inline` updated: emptied container renders `- [x]` (was `- [ ]`); the extended→inline downgrade it targets is unchanged.
- `uv run tox` (all environments) passes.

## Open questions

- None.

## Out of scope

- Archive/list-hiding behavior of newly-`done` root stories (governed by the recently-closed rule; unchanged here).
- Adding a "story" vs "task" distinction to `CONTEXT.md` — "story" is a role (a task that happens to have subtasks), not stored-content vocabulary.
- No ADR: a localized, easily-reversible status rule consistent with the existing "all closed → done" behavior.
