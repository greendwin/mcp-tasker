---
id: s28t11
slug: resolve-merge-wiring-for-order
status: pending
---

# Resolve / merge wiring for order

**Goal**
`tasker resolve` three-way-merges the `order` front-matter field like any other scalar: take the side that changed from base; mark a conflict only if both sides changed it differently. The merged output emits `order:` when set.

**Decisions & constraints**
- `order` is an ordinary front-matter scalar — no cross-file sibling logic. The sort key `(order is None, order, id)` tolerates post-merge gaps and duplicate order values among siblings, so a dumb per-file scalar merge can never corrupt the repo; the next `tasker order` re-densifies.
- Wire `order` into the same field-level merge as `status`/`slug`: extend the merged-scalars dataclass and the merge + emit path in `merge.py`, mirroring how `slug`/`status` are handled.
- Only emit `order:` in merged output when the merged value is set (None omits the line), consistent with slice 1's render rule.

**Edge cases**
- One side sets order, other leaves unset → take the set side.
- Both sides set different orders → conflict marker, like other scalar conflicts.
- Both sides clear (unset) → unset, no line emitted.
- Base had an order, one side cleared it → treat as an ordinary scalar change.

**Key files**
- `src/tasker/merge.py` (`merge_scalar_fields`, the `Merged[...]` scalar dataclass ~lines 21–33 & 118–133, and the emit path ~lines 240–244)
- `src/tasker/resolve.py` (consumes merged fields)

**Acceptance criteria**
- A file where only `ours` changed `order` merges cleanly to the `ours` value.
- Divergent `order` on both sides produces a conflict, consistent with `status`/`slug` conflict handling.
- Merged output includes `order:` only when the resolved value is set; omitted when unset.
- A merged repo with gaps/duplicate orders still loads and sorts sensibly (no invariant violation).
