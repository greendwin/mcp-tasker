---
id: s12t1302
slug: letter-assignment-over-active-todo
status: done
---

# Letter assignment over active todo tasks

Add a helper that maps todo task IDs to shortcut letters (`ta`..`tz`) based on the insertion-ordered todo list, skipping closed tasks.

## Behaviors to test

1. Empty todo list → empty mapping.
2. Three active tasks in order → `{id1: "ta", id2: "tb", id3: "tc"}`.
3. Closed tasks are skipped: [active, closed, active] → `{id1: "ta", id3: "tb"}`.
4. More than 26 active tasks: first 26 get letters, rest get no entry in the mapping (no error).
5. Letters are stable across calls when the input list is unchanged.

## Notes
- Public function lives in `todo.py` (e.g. `assign_todo_letters(tasks: list[Task]) -> dict[str, str]`).
- Pure function over a task list; no I/O. Repo lookup happens at the call site.
- Tests use lightweight `Task` instances; no repo fixture needed.
