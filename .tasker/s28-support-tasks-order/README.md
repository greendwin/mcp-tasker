---
id: s28
slug: support-tasks-order
status: done
---

# Support tasks order

## Context

Tasks currently sort strictly by id: root stories by id, subtasks by physical file order (which equals id order since `add` appends). There's no way to express *implementation order* — the sequence work should happen in — without renaming ids. We introduce an `order` field: a per-sibling-set manual sort key. Tasks with an order sort ahead of unordered ones (ascending); ties and unordered tasks fall back to id. It only has meaning relative to siblings under the same parent.

## Decisions

- **Scope: all sibling sets** — order applies to roots and subtasks at every level; roots are siblings of the virtual root.
- **Sort key** — `key = (order is None, order or 0, id)`: ordered tasks lead ascending, unset tail follows by id. `order: int | None` on the strict `Task` model.
- **Unset sorts last; positive values** — purpose is "pull the next tasks to the front in implementation order," so `1,2,3…` read the obvious way. *Rejected: default-0 with signed ints (order 1 after an unnumbered task is counterintuitive).*
- **Storage: always front-matter `order:` scalar**, written only when set (None omitted → plain tasks byte-unchanged). *Rejected: encoding order in the `## Subtasks` bullet grammar (would touch parse/render/merge/resolve for a plain scalar); rejected: split model with physical subtask order + scalar for roots (non-uniform).*
- **Ordering an inline task auto-upgrades it to a file** (same pattern as `add --details`); clearing order (or a plain `move`) auto-downgrades when nothing else keeps it a file. Consequence: imposing implementation order materializes tasks as files — see ADR 0003. *Rejected: keeping order cheap via bullet storage — we accept file churn to keep the parsers untouched.*
- **CLI `tasker order <anchor> <moved…>`** — group listed siblings into contiguous neighbours, in argument order, positioned at the anchor's slot (anchor gains an order if unset → lands at end of the ordered block); moved tasks are pulled from wherever they were; already-ordered followers shift; unset tail untouched. Refs that live under a different parent are **auto-reparented** to the anchor's parent (ids regenerated, rename mapping printed, source parents auto-downgraded) — no separate flag needed.
- **`--front`** — land the block at the front of the ordered block (`a=1,b=2,…`), shifting previously-ordered tasks down. No symmetric `--back` (YAGNI).
- **`--front <a> --rest`** — materialize a *total* order over every sibling from `a` onward (mass-upgrades inline siblings to files). *Rejected: scoping `--rest` to the already-ordered set only — ordered/unordered are indistinguishable to a user, so silently skipping "unordered" would behave unpredictably.*
- **No `--parent <p>` flag** — *Rejected:* `order` already auto-reparents moved refs to the anchor's parent, so a dedicated `--parent` fully duplicates `move --parent` (re-home to an arbitrary target). To place tasks under an arbitrary parent, run `move --parent` then `order`, or pick an anchor already under the target parent.
- **`--clear <ids…>`** — un-order tasks; remaining ordered siblings renumber; auto-downgrade a task that was a file solely for its order.
- **Sparse values with midpoint insertion** — internal, stepped by 1000; insert between `a<b` → `(a+b)//2`, front → `m//2`; re-space the *whole ordered sibling set* only when a gap can't fit the needed distinct integers. Dense contiguity is a write-time normalization, not a read-time invariant. Values never surface in CLI/MCP — users only express relative placement.
- **MCP `order_tasks(task_refs)`** — one tool doing only base anchor-first neighbour grouping among **same-parent siblings**. Unlike the CLI base command, MCP is **stricter: it rejects cross-parent refs with a structured error and never auto-reparents** — an agent must not implicitly move tasks between parents (use CLI `move`/`order` for that). No `front`/`rest`/`clear` over MCP.
- **Display: sort at display time** in `list` / `view` / `view_tasks`; stored bullet order stays as loaded (keeps reconciliation + byte-stability intact). No visible rank cue — position conveys order.
- **Merge: `order` is an ordinary front-matter scalar** in `resolve` (take the side changed from base; conflict only if both differ). No cross-file sibling logic — the sort tolerates post-merge gaps and duplicates.
- **Field name `order`** (not `rank`) — names the sequence-of-work intent and aligns with the `order` verb and `order_tasks` tool. *Rejected: `rank`/`priority` (drag in importance/score connotations).*

## Open questions

- None outstanding — all grill decisions resolved.

## Out of scope

- Symmetric `--back` flag (push to end) — add later if needed.
- `--parent` flag (re-home to an arbitrary parent) — `order` already auto-reparents to the anchor's parent; use `move --parent` then `order`, or anchor under the target parent.
- Auto-reparenting over MCP — `order_tasks` deliberately rejects cross-parent refs instead (agents should not implicitly move tasks between parents).
- Exposing `--front`/`--rest`/`--clear` over MCP.
- Any visible order/rank indicator in listings.
- Raw-integer order input on any surface.

## Subtasks

- [x] [s28t01](s28t01-order-field-model-parse-render.md): Order field: model, parse, render (round-trip)
- [x] [s28t02](s28t02-display-sort-by-order-id.md): Display sort by (order, id)
- [x] [s28t03](s28t03-clear-order-on-plain-move.md): Clear order on plain move
- [x] [s28t04](s28t04-sparse-reorder-engine-deep-module.md): Sparse reorder engine (deep module)
- [x] [s28t05](s28t05-cli-tasker-order-lt-anchor.md): CLI: tasker order <anchor> <moved...>; (base)
- [x] [s28t06](s28t06-cli-tasker-order-clear.md): CLI: tasker order --clear
- [x] [s28t07](s28t07-cli-tasker-order-front.md): CLI: tasker order --front
- [x] [s28t08](s28t08-cli-tasker-order-front-rest.md): CLI: tasker order --front --rest
- [x] ~~[s28t09](s28t09-cli-tasker-order-parent-attach.md): CLI: tasker order --parent (attach + order)~~
- [x] [s28t10](s28t10-mcp-order-tasks-task-refs.md): MCP: order_tasks(task_refs)
- [x] [s28t11](s28t11-resolve-merge-wiring-for-order.md): Resolve / merge wiring for order
