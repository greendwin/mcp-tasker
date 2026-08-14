---
id: s28t04
slug: sparse-reorder-engine-deep-module
status: done
---

# Sparse reorder engine (deep module)

**Goal**
A pure, disk-free module that computes new order assignments for a sibling set given an operation. Encapsulates all the numbering complexity behind a simple, unit-testable interface: input is the current siblings as `[(id, order|None)]` plus an operation descriptor; output is the new `{id: order}` assignments (only for tasks whose order changes).

**Operations to support (consumed by later CLI/MCP slices):**
- **group-at-anchor** — listed tasks become contiguous neighbours in argument order, positioned at the anchor's slot; anchor gains an order at the end of the ordered block if unset; already-ordered followers shift.
- **group-at-front** — same grouping but the block lands before the current minimum.
- **total-from** — materialize a total order over every sibling from a given task onward (backs `--rest`).
- **clear** — remove listed tasks' orders and renumber the remainder to stay well-spaced.

**Decisions & constraints**
- Sparse values stepped by 1000: first ordered sibling → 1000; append → `max_existing + 1000`.
- Insert one between `a < b` → `(a + b) // 2`; insert before minimum `m` → `m // 2`; a block of K subdivides the target gap into K distinct integers.
- Normalize (re-space the *entire ordered sibling set* to `1000, 2000, …`) ONLY when a gap can't fit the needed distinct integers.
- Dense contiguity is a write-time normalization, not a read-time invariant. Sort tolerates gaps and duplicates.
- Values are internal — never surfaced to CLI/MCP. The step (1000) is a module constant.
- Return only the delta (ids whose order changed) so callers rewrite the minimum number of files.

**Edge cases**
- Anchor unset vs already-ordered.
- Gap of size 1 (adjacent integers) → triggers normalization.
- Moved task currently ordered elsewhere in the same set (pulled out, others close up).
- Front insertion when minimum is already 1 (no room below) → normalize.
- Empty ordered set (first-ever order op).

**Key files**
- New module, e.g. `src/tasker/repo/_order.py` (or `src/tasker/order.py`) — pure functions over `[(id, order)]`.
- Unit tests exercising each operation + the normalization trigger, no filesystem.

**Acceptance criteria**
- group-at-anchor with all-unset siblings assigns the block `1000, 2000, …` and returns only those ids.
- Inserting between `1000` and `2000` yields `1500` and touches no other sibling.
- Inserting between adjacent values triggers whole-set re-spacing to multiples of 1000.
- clear removes the listed ids' orders and leaves the rest well-spaced.
- Given duplicate/gapped input, operations still produce a valid well-spaced result.
