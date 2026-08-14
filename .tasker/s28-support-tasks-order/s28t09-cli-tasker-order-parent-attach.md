---
id: s28t09
slug: cli-tasker-order-parent-attach
status: cancelled
---

# CLI: tasker order --parent (attach + order)

**Goal**
`tasker order --parent <p> <a> <b…>` re-homes the listed tasks under parent `p` (like `move --parent`), then groups them as contiguous neighbours under `p`. Tasks already under `p` are just reordered, not re-homed.

**Decisions & constraints**
- Re-home reuses `move --parent` mechanics: ids regenerated under the new parent, rename mapping printed, source parents auto-downgraded.
- After attaching, the block lands at the end of `p`'s existing ordered block, in argument order (the anchor `a` is newly arrived).
- This is the explicit "move *and* place" path — it does NOT clear order (contrast slice 3, where a plain `move` clears). The order is (re)assigned here by the grouping.
- Flag name is `--parent` with `-p` short (the `--attach` rename, s19t03, was cancelled).
- Short flag: mind collisions with existing global options; confirm `-p` is free on this command.

**Edge cases**
- Some listed tasks already under `p` (reorder only), others elsewhere (re-home then place).
- Re-homing a task that has subtasks (whole subtree moves; its own children's orders are their own sibling concern, untouched).
- Attaching inline tasks: they upgrade to files under `p` as needed to hold order.
- `--parent` combined with `--front`/`--rest`: decide whether allowed; simplest is `--parent` places at end-of-ordered-block (document/tests).

**Key files**
- `src/tasker/cli/_organize_commands.py` (`order --parent`)
- `src/tasker/repo/_move_task.py` (re-home mechanics reused)
- `src/tasker/repo/_order.py` (grouping under new parent)

**Acceptance criteria**
- `tasker order --parent s07 t0301 t0502` moves both under `s07` (mapping printed) and makes them contiguous neighbours at the end of `s07`'s ordered block.
- A task already under `s07` in the same call is reordered without a re-home.
- Source parents auto-downgrade when left empty/file-less, per existing `move` behavior.
