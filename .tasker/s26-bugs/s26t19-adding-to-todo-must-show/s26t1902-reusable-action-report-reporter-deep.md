---
id: s26t1902
slug: reusable-action-report-reporter-deep
status: pending
---

# Reusable action-report reporter (deep module)

## Goal

A reusable, print-only reporter that renders the action-report format from the
ADR: a caller builds a config, adds one item per ref, and prints it.

## Decisions & constraints

- Mirror the `ShowTaskConfig` / `print_tree` idiom:
  - `ActionReportConfig(*, action: str)` — `action` is the header label
    (e.g. `"Adding to TODO"`).
  - `add_item(ref: str, title: str, *, outcome: str | None = None)` accumulates
    items in order.
  - `print_action_report(config)` renders `"<action>:"` then, per item,
    `"  - <ref>: <title>"` plus `"  (<outcome>)"` only when `outcome` is not
    `None`.
- Lives in `src/tasker/cli/_print_utils.py` — the reporter is genuinely general
  (every report-and-preview command will use it), unlike the todo-specific render.
- **Printing-only contract**: uses `console.print`, which is silent under
  `--json-output` (see `utils.py`); emits **no** JSON context itself. Callers own
  all JSON (`task_refs`), matching how `print_tree` leaves `_task_to_json` to its
  callers. *Rejected: the reporter emitting `task_refs` context — conflicts with
  the print-only contract.*
- The bullet uses the plain task id + title (`<id>: <title>`); JSON `task_refs`
  (emitted by the caller, not here) keeps using `task.ref` as today.

## Edge cases

- Empty config (no items) — header still prints? Prefer: print nothing when there
  are no items (a report with no actions is not shown). Confirm via test.
- `outcome=None` → no trailing annotation; `outcome=""` treated same as absent or
  rejected — pick one and test it.
- Markup safety: titles may contain markup characters — escape like the rest of
  `_print_utils` (`escape_markup`).

## Key files

- `src/tasker/cli/_print_utils.py` — add `ActionReportConfig` +
  `print_action_report`.
- `tests/` — new unit test module for the reporter (e.g.
  `tests/test_action_report.py`).

## Acceptance criteria

- `ActionReportConfig(action="Adding to TODO")` + two `add_item` calls +
  `print_action_report` produce the header and both `- id: title` bullets.
- An item with `outcome="already in todo"` renders the `(already in todo)`
  annotation; an item without outcome renders no annotation.
- Under `--json-output`, `print_action_report` prints nothing and adds no JSON
  keys (the reporter never touches context).
- Titles containing markup characters are escaped, not interpreted.
- `uv run tox` passes (all environments).
