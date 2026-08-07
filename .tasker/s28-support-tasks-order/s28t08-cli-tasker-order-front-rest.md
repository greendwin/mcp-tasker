---
id: s28t08
slug: cli-tasker-order-front-rest
status: in-progress
---

# CLI: tasker order --front --rest

**Goal**
`tasker order --front <a> --rest` orders `a` **and every sibling that currently sorts after it** (in current sort order), grouping that block at the front. The block preserves the current relative order of the anchor-onward tasks. Siblings that sort **before** `a` are left unset — they naturally sort after the ordered block. `--rest` may also be used **without** `--front`, appending the anchor-onward tail after a normal group-at-anchor placement.

**Decisions & constraints**
- `--rest` is scoped to the **anchor onward**, not a full total order over the whole sibling set. Earlier siblings keep their existing state (unset stays unset) and fall after the ordered block by the standard sort. Rejected: renumber-everything-including-before-anchor (surprising; touches tasks the user did not name).
- The anchor-onward tail is collected from the last named ref's sibling set **before** any relocation/rename.
- Mass-upgrades the anchor-onward inline siblings to files (potentially a whole story's tail → a directory of files). Accepted cost — see ADR 0003. One command can produce many new files.
- With `--front`, `--rest` is a modifier: `a` + tail-after `a` become the front block. Without `--front`, `--rest` extends the base group-at-anchor: named refs land at the anchor's slot, then the tail-after the last named ref is appended, e.g. `order([a,b,c,x,y], a c, --rest)` → `a, c, x, y, b`.
- Uses the engine's group-at-front / group-at-anchor operations (slice 4).
- Honors ADR 0004: `.recent` (named refs), `--json-output` `task_refs` (the tasks actually reordered), highlight + hierarchy preview.

**Edge cases**
- `a` is currently the first sibling: `--rest` orders the whole set in current order (largely a no-op on sequence, but materializes orders/files for the anchor onward).
- `a` in the middle: `a..end` leads the front block; siblings before `a` stay unset and sort after.
- Named refs already ordered elsewhere: pulled into the block.
- Large sibling sets: verify the upgrade output is coherent and the anchor-onward tail is fully ordered.

**Key files**
- `src/tasker/cli/_organize_commands.py` (`--rest` on `order`, with and without `--front`)
- `src/tasker/repo/_order.py` (group-at-front / group-at-anchor) + repo bulk inline→file upgrade path

**Acceptance criteria**
- Given ordered `t02,t05,t08,t11`, `tasker order --front t08 --rest` yields sequence `t08, t11, t02, t05`: the anchor-onward block (`t08,t11`) leads; earlier `t02,t05` follow in their existing order.
- `order --front <a> --rest` orders the anchor and every sibling after it; siblings before the anchor remain unset (no file) and sort after the ordered block.
- Applied to a story of inline subtasks, every sibling from the anchor onward becomes a file and gains a well-spaced order.
- `--json-output order --front <a> --rest` reports `task_refs` as the tasks actually reordered (anchor + tail), not the untouched earlier siblings.
- `--rest` **without** `--front`: named refs land at the anchor's slot and the tail after the last named ref is appended — `order a c --rest` over `a,b,c,x,y` yields `a, c, x, y, b`.
