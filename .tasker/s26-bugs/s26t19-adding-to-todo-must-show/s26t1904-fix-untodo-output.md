---
id: s26t1904
slug: fix-untodo-output
status: pending
---

# Fix `untodo` output

## Goal

`tasker untodo <refs>` prints the action report, then the updated TODO list with
the just-detached task highlighted (showing it now carries **no**
`(todo)`/`(tX)` marker), handling the empty-list and pinned-via-ancestor cases.

## Decisions & constraints

- Replace `print_parent_preview` in `cmd_untodo`, symmetric with `todo`: build an
  `ActionReportConfig(action="Removing from TODO")`, then render via the
  `_todo_view` helper from the `todo` slice.
- **Detached-task overlay**: after removal, the removed task is no longer in the
  TODO list — add it to the render as a highlighted extra so the user sees it
  without a todo marker (even when the active list is otherwise empty or would
  filter it out).
- **Last-pin removed → empty**: when the final `todo_ids` is empty after the
  batch, print a distinct "that was the last one — TODO list now empty" message
  **and** show the open-tasks fallback (reuse the `list --todo` empty→open-leaf
  path), still highlighting the touched task(s). This is the one place the
  open-tasks fallback is intentionally shown.
- **Pinned-via-ancestor warning**: the TODO list stores task ids; a pinned parent
  renders open descendants that are not in `todo_ids`, so `remove_todo` returns
  `False`. On `False`, walk `get_parent` against `load_todo_ids`; if a pinned
  ancestor exists, set the item outcome to a warning naming it (e.g.
  `"in TODO via pinned parent <ancestor-ref> — untodo <ancestor-ref> to remove
  it"`), leave the task in `todo_ids`, and highlight **both** the child and the
  pinned ancestor in the render. Only when no pinned ancestor exists keep the
  plain `(was not in todo)` outcome.
- Batch: final-state (empty vs active) decided once from the final `todo_ids`.
- JSON unchanged: command emits `task_refs` via `console.append_context` per
  reported ref (append for every reported item, matching today's unconditional
  append). Keep `save_recent_for_refs`.
- No task IDs in code comments (project rule).

## Edge cases

- `untodo` a task never in the list and with no pinned ancestor → `(was not in
  todo)`, list rendered as-is (idempotent behaviour preserved:
  `test_untodo_idempotent`).
- `untodo` the last active pin while closed pins remain → decide empty vs
  all-finished consistently (empty only when `todo_ids` is truly empty).
- Multiple refs where some remove and some hit the pinned-ancestor warning → each
  bullet annotated independently; single render with all touched (and any pinned
  ancestors) highlighted; empty/last-one computed from the final state.
- Removed task is a subtask whose parent is open but not pinned → shows as its own
  highlighted block (nearest visible ancestor logic in `print_tree`).

## Key files

- `src/tasker/cli/_todo_commands.py` — rewrite `cmd_untodo`'s tail.
- `src/tasker/cli/_todo_view.py` — extend render helper for detached overlay +
  empty→fallback (reuse `list_open_leaf_tasks`).
- `tests/test_todo_commands.py` — update `test_untodo_prints_confirmation` to the
  new format; add detached-highlight, pinned-via-ancestor, and last-pin-empty
  tests.

## Acceptance criteria

- Output shows `Removing from TODO:` header + `- <id>: <title>` bullet(s).
- The just-detached task appears highlighted with **no** `(todo)`/`(tX)` marker.
- `untodo` of the last pin prints the last-one/empty message **and** the
  open-tasks fallback listing.
- `untodo <child-of-pinned>` warns naming the pinned ancestor, leaves the task in
  `todo_ids`, and highlights both child and ancestor.
- `untodo` a task with no pinned ancestor still shows `(was not in todo)`
  (idempotent case preserved).
- `--json-output` still yields `task_refs` only (existing `test_untodo_json_output`
  passes unchanged).
- `uv run tox` passes (all environments).
