---
id: s28t02
slug: display-sort-by-order-id
status: pending
---

# Display sort by (order, id)

**Goal**
`list`, `view`, and MCP `view_tasks` present siblings sorted by implementation order: ordered tasks lead (ascending), the unset tail follows by id. A file with a manually-set `order:` is now visibly honored.

**Decisions & constraints**
- Sort key wherever siblings are presented: `key = (task.order is None, task.order or 0, task.id)` — `is None` (not `is not None`): `False (0) < True (1)` puts ordered first, unset tail last, ties by id.
- Sort at **display time only**. Do NOT sort `task.subtasks` in the loaded model or on render — that would rewrite stored bullet order and collide with the `_task_loader.py` id-list reconciliation and byte-stability guarantees.
- Roots: replace `sorted(..., key=lambda p: p.id)` at `_print_utils.py:169`. Subtasks: apply the same key wherever children are iterated for display (`print_task`, `_collect_print_entries`, MCP view rendering).
- No visible rank cue — position conveys order (keeps output clean, per the minimal-styling guideline).

**Edge cases**
- Mixed sibling set (some ordered, some not): ordered block first ascending, then unset by id.
- Duplicate/gapped order values (possible post-merge): tie-break by id; no crash, no normalization at read time.
- Closed/cancelled siblings shown under `--all`: same sort key applies uniformly.

**Key files**
- `src/tasker/cli/_print_utils.py` (root sort at :169; subtask iteration in `print_task` / `_collect_print_entries`)
- `src/tasker/cli/_view_commands.py` (view/list)
- `src/tasker/mcp/_view_methods.py` (view_tasks rendering)

**Acceptance criteria**
- Given siblings with orders `{a:2000, b:1000}` and unset `c, d`, display order is `b, a, c, d` (unset by id).
- Setting no orders yields the current behavior (all by id).
- Rendering/round-tripping the parent file after a `list`/`view` leaves the stored `## Subtasks` bullet order unchanged (display sort does not mutate storage).
