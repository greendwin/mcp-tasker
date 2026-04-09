---
id: s25t0204
slug: add-list-todo-filter-mode
status: done
---

# Add `list --todo` filter mode

Add `--todo` flag to `list` command that shows only todo-marked tasks merged under common parent trees.

Design decisions:
- Todo tasks go through parent-chain merging in `build_print_entries` (shown under common parents)
- Positional `task_refs` add extra tasks to the view (without highlight)
- `--todo` and `--archived` can be combined
- `--all` works as usual (shows closed subtasks)
- Empty todo with no positional refs shows "No tasks to show."
- JSON output uses same format as regular `list`
- No short alias for `--todo`
