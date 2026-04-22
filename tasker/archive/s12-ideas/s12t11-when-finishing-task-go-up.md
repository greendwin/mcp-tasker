---
id: s12t11
slug: when-finishing-task-go-up
status: done
---

# When finishing task -- go up in preview until show first non-finished ancestor

When finishing or cancelling a task via CLI (`done`/`cancel`), improve the preview in `print_parent_preview` (`_print_utils.py`):

1. For each closed task, walk up via `get_parent` until finding a non-closed (`not is_closed`) ancestor.
2. Call `show_task` on that ancestor with `SHOW_OPENED` — the finished task appears naturally in the subtree.
3. Deduplicate — if multiple tasks resolve to the same ancestor, show it once.
4. Fallback: only if **every** task's chain ended at a closed root (no non-closed ancestor for any task), show all non-closed root tasks as a "what's next?" listing.

All changes in `print_parent_preview`. No changes to `cmd_done_task` or `cmd_cancel_task`.
