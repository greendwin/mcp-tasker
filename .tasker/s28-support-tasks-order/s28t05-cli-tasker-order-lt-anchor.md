---
id: s28t05
slug: cli-tasker-order-lt-anchor
status: in-progress
---

# CLI: tasker order <anchor> <moved...>; (base)

**Goal**
`tasker order <anchor> <moved…>` reorders sibling tasks in place: the listed tasks become contiguous neighbours, in argument order, positioned at the anchor's slot. Order values (from the reorder engine) are written to front matter; any listed inline task auto-upgrades to a file to hold its order. Works at both subtask scope and root (story) scope.

**Decisions & constraints**
- Scope is the anchor's sibling set — the anchor's parent's subtasks, or the root story list when the anchor is a root task (no parent).
- Moved refs that live under a different parent are first relocated, then ordered — two distinct cases: (a) anchor is a subtask → moved refs relocate under the anchor's parent; (b) anchor is a root task → moved subtasks are promoted to root. No cross-parent error.
- On success the command reports its result: relocated (renamed) tasks are printed, and the moved/ordered tasks are shown at their new position and highlighted. `--json-output` emits the same result as structured json.
- Test harness surfaces bugs: `catching_errors` is mocked in tests so only `TaskerError` + Typer/Click exceptions go through the production path (clean `Error:` exit 1); every other (unexpected) exception bubbles straight to the test. Production error handling is unchanged; tests asserting production's generic-exception wrapping opt out via the `real_error_handling` marker.
- Anchor holds its position relative to untouched ordered tasks; if the anchor is unset it gains an order at the end of the ordered block. Moved tasks are pulled from wherever they were (ordered elsewhere or unset). Already-ordered followers shift. The unset tail is never touched.
- Single arg `tasker order <a>` (no moved refs) is a true no-op: nothing changes on disk, and a warning tells the user at least one task to move is required.
- Setting a non-default order on an inline task auto-upgrades it to basic form — same pattern as `add --details`.
- Uses the sparse reorder engine (group-at-anchor); rewrites only the files whose order actually changed.
- Running the command updates the recent-tasks list for the referenced tasks.
- Task-id args support the standard autocompletion like other commands.

**Edge cases**
- A moved task already ordered before the anchor (removing it shifts the anchor earlier relative to remaining siblings).
- Mix of inline and file-based moved tasks (some upgrade, some already files).
- Moved refs spanning parents/roots → relocated under the anchor's parent (or root), then ordered.
- Anchor is a root task and a moved ref is a subtask → the subtask is promoted to root scope (distinct from relocating under a subtask parent).
- Root-scope reordering where some root tasks are unset and some already ordered.
- A command's internals raise an unexpected exception → in tests it surfaces (bubbles) rather than being hidden behind a generic `Error:` exit 1.

**Key files**
- `src/tasker/cli/_organize_commands.py` (the `order` command)
- `src/tasker/repo/_order.py` (engine) + repo write path for order + inline→file upgrade
- `src/tasker/repo/_task_repo.py` / loader for upgrade + parent/root collection + move mechanics
- `src/tasker/resolve.py` (`save_recent_for_refs` — recent-list update)

**Acceptance criteria**
- `tasker order t08 t02 t20` makes `t08, t02, t20` contiguous in that order at `t08`'s slot; verify via `view`/`list` ordering.
- A listed inline subtask becomes a file after ordering.
- Only the reordered files change on disk (untouched siblings unmodified).
- A moved ref under a different parent is relocated under the anchor's parent and then ordered (no cross-parent error).
- Reordering root-level tasks works — `order <s-anchor> <s-moved…>` reorders stories at root scope (anchor has no parent).
- Running `order` updates the recent-tasks list for the referenced tasks.
- Single-arg `order <a>` is a true no-op and warns that at least one task to move is required.
- Anchor is a root task + a moved ref is a subtask → the subtask is promoted to root and ordered after the anchor (distinct from relocating under a subtask parent).
- Relocated (renamed) tasks are printed in `order`'s output.
- Moved/ordered tasks are reported at their new position (argument order) and highlighted.
- `--json-output order …` emits a structured result (deferred to a later batch).
- Test harness: unexpected (non-typer, non-`TaskerError`) exceptions bubble directly to the test via a mocked `catching_errors`; `TaskerError`/Typer errors keep the production clean-`Error:` path. Production unchanged; `real_error_handling` marker opts specific tests back to production wrapping.
