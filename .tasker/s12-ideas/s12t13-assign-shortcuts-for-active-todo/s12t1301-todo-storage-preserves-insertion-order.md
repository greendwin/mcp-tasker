---
id: s12t1301
slug: todo-storage-preserves-insertion-order
status: done
---

# TODO storage preserves insertion order

Switch `todo.py` from `set[str]` to `list[str]` so the TODO file order reflects the order in which tasks were added.

## Behaviors to test (red-green per behavior)

1. Adding tasks A, B, C in order produces a file with A, B, C in that order.
2. Removing B from [A, B, C] leaves [A, C] (no reorder).
3. Re-adding A to [A, B, C] is a no-op — order stays [A, B, C].
4. `load_todo_ids` reads back the same order it was written in.
5. Existing repos with lex-sorted files load without error (back-compat).

## Notes
- Public surface: `add_todo`, `remove_todo`, `load_todo_ids`/`load_todo_tasks`, `save_todo_ids` signatures.
- Rename to `load_todo_ids`/`save_todo_ids` returning/accepting `list[str]` is acceptable; update all callers.
- Tests should exercise file round-trips through the public API, not inspect private state.
