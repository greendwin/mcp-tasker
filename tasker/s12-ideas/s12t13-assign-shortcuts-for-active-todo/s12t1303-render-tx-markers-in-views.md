---
id: s12t1303
slug: render-tx-markers-in-views
status: done
---

# Render `(tX)` markers in views

Update `compute_markers` in `_print_utils.py` to render `(tX)` for tasks with an assigned shortcut, falling back to `(todo)` for unassigned/closed/overflow.

## Behaviors to test (CLI integration via `assert_invoke`)

1. `task list --todo` shows `(ta)`, `(tb)`, `(tc)` next to the first three active todo tasks in order.
2. A closed task on the todo list shows `(todo)` (no letter).
3. With 27+ active todo tasks, the 27th and beyond show `(todo)` (no letter); first 26 show `(ta)`..`(tz)`.
4. Full `task list` (no `--todo`) shows the same `(tX)` markers next to todo'd tasks deep in the tree.
5. `task todo <ref>` parent preview output renders `(tX)` for the newly added task.

## Notes
- Single edit point: `compute_markers`. Build the letter map once from `load_todo_ids` + repo lookup.
- Tests should be CLI-level (`assert_invoke`), asserting on output strings.
