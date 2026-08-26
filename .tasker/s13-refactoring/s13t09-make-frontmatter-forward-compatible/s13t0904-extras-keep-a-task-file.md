---
id: s13t0904
slug: extras-keep-a-task-file
status: pending
---

# Extras keep a task file-based (block downgrade to inline)

## Goal

A task carrying frontmatter extras is never downgraded to an inline subtask
bullet — an inline bullet has no frontmatter, so downgrade would silently
delete third-party annotations. Extras survive every tasker edit path
end-to-end.

## Decisions & constraints

- Add a `task.extra` guard next to the existing `task.description` check in
  `update_task_status_and_flags` (`src/tasker/repo/_utils.py`,
  `allow_downgrade` branch). This extends ADR 0003's "no other reason to be a
  file" rule: extras are such a reason.
- In practice downgrade triggers via `order --clear` → `try_downgrade_task`;
  the guard belongs in the shared helper, not the command.

## Edge cases

- `order --clear` on a task with extras and no description/subtasks: order key
  is cleared but the file remains, extras intact.
- Task with empty `extra` dict ({}) downgrades normally — only non-empty extras
  block.
- Downgrade of a sibling without extras still works (guard is per-task).

## Key files

- `src/tasker/repo/_utils.py` — `update_task_status_and_flags`
- `tests/test_task_repo.py`, `tests/test_order_commands.py`

## Acceptance criteria

- `order --clear` on an extras-carrying, otherwise-inline-eligible task leaves
  it file-based with extras preserved on disk.
- The same scenario without extras still downgrades to inline.
- `uv run tox` passes (all environments).
