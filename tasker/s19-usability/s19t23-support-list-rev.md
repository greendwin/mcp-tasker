---
id: s19t23
slug: support-list-rev
status: done
---

# Support `list --rev` / `--in-review`

Add a `list` view that surfaces every task awaiting review across the repo.

## Behavior

- New flag with two aliases: `--rev` and `--in-review` (single bool option).
- Walks every active root recursively and lists each task whose status is
  `in-review` (reuse the existing `_iter_in_review_tasks` helper from
  `_status_commands.py`). Archived roots are not walked.
- Each listed task is rendered with its parent shown above it, matching the
  existing `cmd_list_tasks` render loop.
- `--all` is honored and forwarded as `show_children_mode=SHOW_ALL` (no-op
  in practice since in-review is leaf-only today, but kept consistent).
- Explicit `task_refs` are additive — they are appended to the in-review
  set and rendered alongside.
- Mutually exclusive with `--archived`, `--todo`, and `--closed`.

## Empty fallback

When `--rev` finds zero in-review tasks **and** no `task_refs` were given:

- Print `No tasks in review.` in green.
- Then render active root trees (default `list` output), excluding roots
  whose own status is closed (`task.is_closed`).

If `task_refs` were given, do not trigger the fallback — render only the
explicit refs.

## Help text

`Show tasks awaiting review. Falls back to active root tasks when none. Mutually exclusive with --archived, --todo, and --closed.`

## Scope

- CLI-only change in `cmd_list_tasks` (`_view_commands.py`).
- Promote `_iter_in_review_tasks` to a shared location (or import from
  `_status_commands`) — no behavior change to that helper.
- MCP `list_tasks` is not extended in this task.

## Tests

1. `--rev` with several in-review tasks across roots → flat list with
   parents above each.
2. `--in-review` alias works identically to `--rev`.
3. `--rev` with zero in-review tasks → green `No tasks in review.` header
   followed by active root trees.
4. Empty fallback excludes roots whose own status is closed.
5. `--rev` with explicit `task_refs` → in-review tasks plus the refs; no
   fallback even when in-review set is empty.
6. `--rev --all` → forwarded to `SHOW_ALL` children mode (renders subtree
   if any).
7. `--rev --archived`, `--rev --todo`, `--rev --closed` → each errors
   with `BadParameter`.
