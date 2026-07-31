---
id: s28t08
slug: cli-tasker-order-front-rest
status: pending
---

# CLI: tasker order --front --rest

**Goal**
`tasker order --front <a> --rest` materializes a *total* order over every sibling from `a` onward (in current sort order): `a` and everything that currently sorts at/after it move to the front as a block preserving relative order, and the siblings that sorted before `a` are renumbered after them. Every sibling from `a` onward becomes ordered.

**Decisions & constraints**
- `--rest` is deliberately **total**, not scoped to the already-ordered set. Rationale: ordered and unordered tasks are indistinguishable to a user reading a listing, so a `--rest` that silently skipped "unordered" ones would behave unpredictably. Rejected: rotate-ordered-set-only.
- Consequence: this mass-upgrades inline siblings to files (potentially a whole story's subtask list → a directory of files). This is the accepted cost — see ADR 0003. One command can produce many new files.
- `--rest` is a modifier on `--front`; uses the engine's total-from operation (slice 4).

**Edge cases**
- `a` is currently the first sibling: `--rest` orders the whole set in current order (largely a no-op on sequence, but materializes all orders/files).
- `a` in the middle: rotation — `a..end` to front, `start..a-1` after.
- Large sibling sets: verify the rename/upgrade output is coherent and the resulting order is a clean total order.

**Key files**
- `src/tasker/cli/_organize_commands.py` (`--rest` on `order`)
- `src/tasker/repo/_order.py` (total-from) + repo bulk inline→file upgrade path

**Acceptance criteria**
- Given ordered `t02=1,t05=2,t08=3,t11=4`, `tasker order --front t08 --rest` yields sequence `t08, t11, t02, t05`.
- Applied to a story of inline subtasks, every sibling from the anchor onward becomes a file and gains a well-spaced order.
- The resulting sibling set is a clean total order (no unset tail remaining from the anchor onward).
