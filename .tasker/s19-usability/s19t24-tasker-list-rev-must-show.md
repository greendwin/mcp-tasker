---
id: s19t24
slug: tasker-list-rev-must-show
status: done
---

# Tasker list --rev must show --todo if nothing in review

When `list --rev` finds no in-review tasks, fall back to the TODO list
instead of active root tasks — but only when the TODO list contains at
least one **active** (non-closed) pinned task. If the TODO list is empty
or every pinned task is finished, keep today's active-roots fallback.

## Behavior

1. In-review tasks exist → unchanged (current behavior).
2. No in-review + TODO has ≥1 active pinned task → header
   `No tasks in review.` followed by a `Showing TODO list:` sub-note,
   body rendered identically to `list --todo` (same letter markers,
   ordering, hide-finished rule).
3. No in-review + TODO empty *or* all pinned tasks finished → existing
   active-roots fallback (unchanged green header, no sub-note).
4. Explicit task refs remain additive on top of whichever fallback fires
   (same contract as today).
5. CLI-only — MCP `list_tasks` is **not** extended in this task.

## Tests (TDD)

- in-review present → existing behavior preserved
- no in-review + active TODO → renders TODO list with sub-note
- no in-review + empty TODO → active-roots fallback (unchanged)
- no in-review + TODO all-finished → active-roots fallback (not TODO)
- explicit refs additive in the TODO-fallback branch
