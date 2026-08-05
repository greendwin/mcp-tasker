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
- Moved refs that live under a different parent are first relocated under the anchor's parent (or to root, when the anchor is a root task), then ordered. No cross-parent error.
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
- Root-scope reordering where some root tasks are unset and some already ordered.

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
