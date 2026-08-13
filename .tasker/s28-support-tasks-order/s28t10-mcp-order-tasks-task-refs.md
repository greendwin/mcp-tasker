---
id: s28t10
slug: mcp-order-tasks-task-refs
status: done
---

# MCP: order_tasks(task_refs)

**Goal**
A single MCP tool `order_tasks(task_refs)` that does only the base anchor-first neighbour grouping — "put these siblings next to each other in this order" (equivalent to CLI `tasker order <anchor> <moved…>`). Returns the concise ack (`{id, status}`-style, with affected refs / resulting order).

**Decisions & constraints**
- Minimal surface: NO `front` / `rest` / `parent` / `clear` over MCP. Agents mostly just need "task X after task Y"; the richer flags stay CLI-only.
- `task_refs` are anchor-first (first ref is the anchor), same-parent siblings; supports the shortcut refs (`q`, `p`, `ta`, …) like other MCP task_ref params.
- Reuses the exact repo path behind the CLI base command (slice 5) — no separate logic.
- Follows the existing MCP ack convention; add `affected` when the operation renumbers/upgrades additional siblings.

**Edge cases**
- Non-sibling refs → structured error, consistent with other MCP tools.
- Inline tasks in the list upgrade to files (same as CLI base).
- Single ref behaves as the CLI base single-ref case.

**Key files**
- `src/tasker/mcp/` — new method (e.g. `_order_methods.py`) + tool registration in the MCP server
- `src/tasker/mcp/_render.py` (ack shaping)
- Shared repo path from slice 5

**Acceptance criteria**
- `order_tasks(["s19t08","s19t02","s19t20"])` groups those siblings contiguously in that order; a follow-up `view_tasks` reflects it.
- Tool is registered and documented alongside the other mutating MCP tools; returns the concise ack.
- No front/rest/parent/clear parameters are exposed.
