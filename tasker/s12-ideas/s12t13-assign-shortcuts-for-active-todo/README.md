---
id: s12t13
slug: assign-shortcuts-for-active-todo
status: pending
---

# Assign shortcuts for active todo tasks

Assign single-letter shortcuts (`ta`..`tz`) to active todo tasks for quick referencing, replacing the `(todo)` marker.

# Design

## Shortcut format
- `ta`..`tz` — letters only, 26 slots, no hard cap.
- Child paths supported: `taNN`, `taNNNN` (mirrors existing `qNN` syntax).
- Tasks beyond `tz` and closed tasks render as plain `(todo)`.

## Assignment
- Position-based over the TODO list in insertion order.
- Skip `is_closed` tasks (done/cancelled) when assigning letters.
- Re-adding an existing todo task is a no-op (no rebind, no reorder).
- Removing a task shifts later letters left on next render.

## Storage
- `TODO_FILE` keeps "one ID per line" but becomes order-significant.
- `todo.py` switches `set[str]` → `list[str]` throughout.
- Existing repos start in lex order on first read; no migration needed.

## Resolution
- Rename `_resolve_recent` → `_resolve_shortcut` in `resolve.py`.
- Add `t<letter>(NN)*` branch alongside existing `q`/`p` branches.
- `t<letter>` resolution does NOT update the recent task (consistent with `q`/`p`).

## Rendering
- `compute_markers` in `_print_utils.py` builds the letter map once per render.
- Renders `(tX)` if letter assigned, `(todo)` otherwise.
- All views (list, list --todo, parent previews, show) inherit the change.

## MCP parity
- Route MCP per-method `repo.resolve_ref` calls through the CLI's `resolve_ref` helper.
- Gives MCP full `q`/`p`/`t<letter>` shortcut support in one refactor.

## Discoverability
- `task list --todo` is the canonical way to see the letter→task mapping.
- No separate legend command.

## Subtasks

- [x] [s12t1301](s12t1301-todo-storage-preserves-insertion-order.md): TODO storage preserves insertion order
- [ ] [s12t1302](s12t1302-letter-assignment-over-active-todo.md): Letter assignment over active todo tasks
- [ ] [s12t1303](s12t1303-render-tx-markers-in-views.md): Render `(tX)` markers in views
- [ ] [s12t1304](s12t1304-resolve-tletter-shortcuts-in-cli.md): Resolve `t<letter>` shortcuts in CLI
- [ ] [s12t1305](s12t1305-mcp-routes-through-shared-shortcut.md): MCP routes through shared shortcut resolver
