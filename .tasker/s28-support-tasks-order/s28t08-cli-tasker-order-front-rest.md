---
id: s28t08
slug: cli-tasker-order-front-rest
status: done
---

# CLI: tasker order --front --rest

**Goal**
`tasker order --front <a> --rest` orders `a` **and every sibling that currently sorts after it** (in current sort order), grouping that block at the front. The block preserves the current relative order of the anchor-onward tasks. Siblings that sort **before** `a` are left unset — they naturally sort after the ordered block. `--rest` may also be used **without** `--front`, appending the anchor-onward tail after a normal group-at-anchor placement.

**Decisions & constraints**
- **Rule 1 — parent is the anchor's.** The anchor (first ref; for `--front`, the first in the list) fixes the target scope. Every other ref moves to become the anchor's sibling. This is one rule covering the whole source×target matrix: subtask-from-another-parent relocates, a named root task **demotes** to a subtask under the anchor's parent, and when the anchor is a root task a named subtask **promotes** to root.
- **Rule 2 — `--rest` keys off the *last* ref, computed *before* any rename/reparent.** The tail = the last ref's siblings that sort after it, taken from its **original** parent before anything moves. `order s5t1 s2t3 --rest` means `s2t3, s2t4, …` (s2t3's original siblings), NOT s5's; that whole tail then moves with the block under the anchor's (s5t1's) parent.
- `--rest` is scoped to the **last ref onward**, not a full total order over the whole sibling set. Siblings before the last ref keep their existing state (unset stays unset) and fall after the ordered block by the standard sort. Rejected: renumber-everything (surprising; touches tasks the user did not name).
- Mass-upgrades the tail inline siblings to files (potentially a whole story's tail → a directory of files). Accepted cost — see ADR 0003. One command can produce many new files.
- With `--front`, `--rest` is a modifier: the last ref + its tail lead the front block. Without `--front`, `--rest` extends the base group-at-anchor: named refs land at the anchor's slot, then the last ref's tail is appended, e.g. `order([a,b,c,x,y], a c, --rest)` → `a, c, x, y, b`.
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
- Rule 2 cross-parent: `order s5t1 s2t3 --rest` groups `s5t1` then `s2t3` and s2t3's original tail (`s2t4, …`) under `s5t1`'s parent — the tail is s2t3's siblings, not s5t1's.
- Reparenting matrix holds in every mode (`--front`, `--front --rest`, `--rest`): source and target may each be a subtask or a root task; source is always moved to become the anchor's sibling (relocate / demote / promote) and ordered correctly.
