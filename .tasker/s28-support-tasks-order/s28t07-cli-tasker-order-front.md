---
id: s28t07
slug: cli-tasker-order-front
status: in-review
---

# CLI: tasker order --front

**Goal**
`tasker order --front <a> <b…>` groups the listed siblings into contiguous neighbours (arg order) and lands the block at the **front** of the ordered block, shifting previously-ordered tasks down. The unset tail is untouched.

**Decisions & constraints**
- With `--front`, the first ref is not a positional anchor — it's just the first element of the block placed at the front.
- Reuses the engine's group-at-front operation (slice 4). Front insertion lands the block **below the current minimum**; when there is no integer room below, the block goes **negative** — the engine never re-spaces the existing set. The result still sorts correctly (negatives lead).
- No symmetric `--back` flag (YAGNI — push-to-back is expressible by ordering the others ahead).
- Moved refs under a different parent are relocated under the first ref's parent (or promoted to root) before ordering — same mechanics as the base command; no cross-parent error.
- Same inline→file auto-upgrade as the base command.
- `--clear` is mutually exclusive with `--front` (and `--rest`); combining them is a usage error.
- Honors ADR 0004: updates `.recent` (named refs), emits `--json-output` `task_refs`, highlights and previews the moved tasks in the updated hierarchy.

**Edge cases**
- No existing ordered siblings: block simply becomes `1000, 2000, …`.
- Current minimum already low / no integer room below → block goes negative; result still sorts correctly.
- Some listed tasks already ordered elsewhere: pulled to the front block.
- A lone `--front <a>` is meaningful (moves `a` to the front), not a no-op — no "at least one task" warning.

**Key files**
- `src/tasker/cli/_organize_commands.py` (`--front` flag on `order`)
- `src/tasker/repo/_order.py` (group-at-front)

**Acceptance criteria**
- Given ordered `t02,t05,t08,t11`, `tasker order --front t08` makes `t08` first, others shift down.
- `tasker order --front a b` places `a` then `b` ahead of all previously-ordered siblings, in argument order.
- Front insertion with no integer room below goes negative; result still sorts correctly (no whole-set re-spacing).
- A lone `--front <a>` moves `a` to the front and does not warn about missing moved refs.
- A listed inline task is upgraded to a file to hold its order.
- `order --clear --front …` (or `--rest`) reports a usage error naming `--clear`.
- Running `order --front` updates `.recent`, emits structured `task_refs` under `--json-output`, and previews the moved tasks highlighted in the updated hierarchy.
