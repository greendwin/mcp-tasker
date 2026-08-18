---
id: s26t1903
slug: fix-todo-output
status: done
---

# Fix `todo` output

## Goal

`tasker todo <refs>` prints the action report, then the *updated TODO list* —
never the all-open sprawl — with the touched task(s) highlighted.

## Decisions & constraints

- Replace the `print_parent_preview` call in `cmd_todo` with: build an
  `ActionReportConfig(action="Adding to TODO")` across the batch loop
  (`add_item(task.ref, task.title, outcome=...)`, outcome `"already in todo"` when
  `add_todo` returns `False`, else `None`), print it, then render the updated TODO
  list once.
- Create `src/tasker/cli/_todo_view.py`:
  - Move `_collect_todo_tasks` here from `_view_commands.py` (update the import in
    `_view_commands.py`; behaviour of `list --todo` unchanged).
  - Add a render helper (e.g. `print_todo_result(repo, *, touched, ...)`) that
    computes final state via `classify_todo`/`load_todo_tasks` and renders the
    active TODO list (active-only), overlaying the `touched` tasks with
    `highlight=True`. Pure text (like `print_tree`).
- `All tasks finished!` when the post-add active set is empty (a `done` task is
  the only/all pins), showing the closed pins with the touched task highlighted —
  mirror `list --todo`.
- Do **not** trigger the open-tasks fallback on the add path (the list is never
  empty after an add; the fallback belongs only to `untodo`-to-empty in the next
  slice).
- JSON unchanged: emit `task_refs` via the command (e.g.
  `console.append_context("task_refs", task.ref)` per ref), not via the printing
  helpers. Keep `save_recent_for_refs`.
- `tasker/todo.py` stays pure domain (no console).
- No task IDs in code comments (project rule).

## Edge cases

- Multiple refs → one report block (a bullet per ref) then a single render from
  the final state.
- Re-adding an already-pinned task → `(already in todo)` annotation; still shown
  highlighted in the render.
- `todo` a `done` task while other active pins exist → active list shown, the
  done task highlighted among/after them (per `list --todo` active filter it may
  sort with closed pins; ensure it still appears because it is a touched
  highlight).
- Recent `(q)`/`(p)` and `(todo)`/`(tX)` markers still render (come free from
  `print_tree`).

## Key files

- `src/tasker/cli/_todo_commands.py` — rewrite `cmd_todo`'s tail.
- `src/tasker/cli/_todo_view.py` — new module (render + moved `_collect_todo_tasks`).
- `src/tasker/cli/_view_commands.py` — update import of `_collect_todo_tasks`.
- `src/tasker/cli/_print_utils.py` — consume `ActionReportConfig`/`print_action_report`.
- `tests/test_todo_commands.py` — update `test_todo_prints_confirmation` to the new
  format; add regression + format + all-finished tests.

## Acceptance criteria

- **Regression:** with an open non-todo story present, `todo <ref>` output does
  **not** list that unrelated open story nor the full open tree (reproduce the
  `todo` of a `done` task case).
- Output shows `Adding to TODO:` header + `- <id>: <title>` bullet(s).
- Re-adding a pinned task shows `(already in todo)`.
- `todo` a `done` task that is the only pin shows `All tasks finished!` and the
  highlighted closed task.
- Multiple refs → one report block, multiple bullets, single rendered result.
- `--json-output` still yields `task_refs` only (existing `test_todo_json_output`
  passes unchanged).
- `list --todo` behaviour unchanged after moving `_collect_todo_tasks`.
- `uv run tox` passes (all environments).
