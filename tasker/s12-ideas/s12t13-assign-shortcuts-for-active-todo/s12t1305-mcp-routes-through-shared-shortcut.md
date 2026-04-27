---
id: s12t1305
slug: mcp-routes-through-shared-shortcut
status: done
---

# MCP routes through shared shortcut resolver

Replace direct `repo.resolve_ref(ref)` calls in MCP methods with the CLI's `resolve_ref` helper from `resolve.py`, gaining `q`/`p`/`t<letter>` support in MCP.

## Behaviors to test (MCP method calls)

1. `view_tasks(["ta"])` returns the first active todo task.
2. `view_tasks(["ta02"])` returns the second child of the `ta`-pointed task.
3. `start_task("ta")` / `finish_task("ta")` / `review_task("ta")` operate on the right task.
4. `view_tasks(["q"])` works (q parity).
5. Direct refs (`view_tasks(["s12t13"])`) continue to work.
6. Calling MCP with a shortcut does NOT update the recent task.

## Notes
- Touch every MCP module under `src/tasker/mcp/` that calls `repo.resolve_ref` (`_view_methods.py`, `_status_methods.py`, `_create_methods.py`).
- The CLI helper returns a `ResolvedRef`; MCP code wants the `.task` field.
