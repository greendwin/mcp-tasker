---
id: s28t07
slug: cli-tasker-order-front
status: pending
---

# CLI: tasker order --front

**Goal**
`tasker order --front <a> <b…>` groups the listed siblings into contiguous neighbours (arg order) and lands the block at the **front** of the ordered block, shifting previously-ordered tasks down. The unset tail is untouched.

**Decisions & constraints**
- With `--front`, the first ref is not a positional anchor — it's just the first element of the block placed at position 1.
- Reuses the engine's group-at-front operation (slice 4); front insertion is `min // 2`, triggering whole-set re-spacing when there's no room below the current minimum.
- No symmetric `--back` flag (YAGNI — push-to-back is expressible by ordering the others ahead).
- Same-parent-siblings constraint and inline→file auto-upgrade as the base command.

**Edge cases**
- No existing ordered siblings: block simply becomes `1000, 2000, …`.
- Current minimum already `1` / no integer room below → normalization.
- Some listed tasks already ordered elsewhere: pulled to the front block.

**Key files**
- `src/tasker/cli/_organize_commands.py` (`--front` flag on `order`)
- `src/tasker/repo/_order.py` (group-at-front)

**Acceptance criteria**
- Given ordered `t02,t05,t08,t11`, `tasker order --front t08` makes `t08` first, others shift down.
- `tasker order --front a b` places `a` then `b` ahead of all previously-ordered siblings.
- Front insertion with no room below re-spaces the whole ordered set; result still sorts correctly.
