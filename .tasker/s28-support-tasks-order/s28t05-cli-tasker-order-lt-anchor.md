---
id: s28t05
slug: cli-tasker-order-lt-anchor
status: pending
---

# CLI: tasker order &lt;anchor&gt; &lt;moved...&gt; (base)

**Goal**
`tasker order <anchor> <moved…>` reorders same-parent siblings in place: the listed tasks become contiguous neighbours, in argument order, positioned at the anchor's slot. Order values (from the reorder engine) are written to front matter; any listed inline task auto-upgrades to a file to hold its order.

**Decisions & constraints**
- All refs must be same-parent siblings; error otherwise (the `--parent` attach path is a later slice).
- Anchor holds its position relative to untouched ordered tasks; if the anchor is unset it gains an order at the end of the ordered block. Moved tasks are pulled from wherever they were (ordered elsewhere or unset). Already-ordered followers shift. The unset tail is never touched.
- Setting a non-default order on an inline task auto-upgrades it to basic form — same pattern as `add --details`.
- Uses the sparse reorder engine (slice 4, group-at-anchor); rewrites only the files whose order actually changed.
- Task-id args support the standard autocompletion like other commands.

**Edge cases**
- Single arg `tasker order <a>`: no-op or assigns `<a>` an order at the end of the block (define and test the chosen behavior).
- A moved task already ordered before the anchor (removing it shifts the anchor earlier relative to remaining siblings).
- Mix of inline and file-based moved tasks (some upgrade, some already files).
- Refs spanning parents/roots → clear error message.

**Key files**
- `src/tasker/cli/_organize_commands.py` (new `order` command)
- `src/tasker/repo/_order.py` (engine) + repo write path for order + inline→file upgrade
- `src/tasker/repo/_task_repo.py` / loader for upgrade mechanics

**Acceptance criteria**
- `tasker order t08 t02 t20` makes `t08, t02, t20` contiguous in that order at `t08`'s slot; verify via `view`/`list` ordering.
- A listed inline subtask becomes a file after ordering.
- Only the reordered files change on disk (untouched siblings unmodified).
- Ordering non-sibling refs errors clearly.
