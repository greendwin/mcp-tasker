---
id: s19t2802
slug: thread-newid-through-move-mechanics
status: done
---

# Thread new_id through move mechanics

## Goal

`repo.move_task(task, *, new_parent, new_id=None)` and `move_task_impl` honor an explicit `new_id`, relabeling the subtree to the exact id and re-homing under the implied parent.

## Decisions & constraints

- Thread `new_id` through `move_task_impl`, bypassing its two no-op short-circuits (`ref.parent_id == new_parent.id`, and `_convert_to_root`'s `is_root_task_id(task.id)`) and the auto-id generation (`get_next_subtask_id`/`find_next_root_task_id`) when `new_id` is set.
- Reuse existing self/descendant guards (`new_parent.id == task.id`, `_is_descendant_of`) and `_reregister_tree` for recursive child relabeling.
- `move_task_impl` stays mechanical — trusts that `new_id` is already validated/free and `new_parent` is the resolved implied parent (None for root targets). Archived flag follows `new_parent` (or False for root), as today.
- `repo.move_task` gains a pass-through `new_id` param.
- *Rejected: a dedicated `rename_task_impl` — chose to extend the existing function so the relabel reuses the same leaf helpers.*

## Edge cases

- same-parent relabel (`s05t03→s05t07`) must NOT early-return.
- root relabel (`s05→s07`) must NOT early-return.
- re-parent (`s05t03→s09t01`); to-root (`s05t03→s07`).
- subtree with children relabels all descendants.

## Key files

- `src/tasker/repo/_move_task.py`, `src/tasker/repo/_task_repo.py`
- tests: `tests/test_task_repo.py`

## Acceptance criteria

- `repo.move_task(t, new_parent=None, new_id="s07")` on a subtask returns renames and the task + children carry the new ids.
- A same-parent `new_id` produces a real rename (non-empty renames), not a no-op.
- Existing `move_task` behavior with `new_id=None` is unchanged.
