---
id: s19t21
slug: dont-show-finished-todo-tasks
status: done
---

# Don't show finished tasks in 'list --todo' when active exists

Filter finished tasks from `list --todo` output (CLI-only).

## Behavior

Load TODO tasks via existing `load_todo_tasks` (unchanged). Partition into
active (`not is_closed`) and finished (`is_closed`, i.e. DONE/CANCELLED).

- **Mixed (some active, some finished):** show only active tasks. After the
  tree, print a dim footer with the hidden count (singular/plural):
  `1 finished task hidden` / `N finished tasks hidden`.
- **All finished:** print `All tasks finished!` (green) header above; show
  the full TODO list as today; highlight the most-recently-closed task using
  existing `highlight=True` (renders ` <<<`). To pick "last finished",
  intersect the finished set with `load_closed_tasks` ordering. If none of
  the finished TODO tasks appear in the recent-closed list, show no
  highlight (header still printed).
- **Empty TODO / all unresolvable:** existing "No tasks to show." path,
  untouched.

## Scope

- CLI-only change in `cmd_list_tasks` (`_view_commands.py`).
- `load_todo_tasks` and MCP `list_tasks(todo=True)` semantics unchanged.
- `--all` bypasses filter, header, and highlight (today's behavior).
- Explicit `task_refs` alongside `--todo` are never filtered.
- Display-only: TODO file is not auto-pruned.

## Tests

1. Mixed → only active shown, footer with plural count.
2. Mixed with exactly 1 finished → footer uses singular form.
3. All finished → header + full list + `<<<` on last-closed (via recent).
4. All finished but none in recent → header + list, no highlight.
5. `--todo --all` with mixed → all shown, no footer/header/highlight.
6. `--todo` with explicit refs → explicit refs not filtered.
7. Empty TODO → "No tasks to show.".
