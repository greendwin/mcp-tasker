---
id: s26t19
slug: adding-to-todo-must-show
status: pending
---

# Adding to todo must show only updated todo list, not all opened

## Context

`tasker todo <ref>` and `tasker untodo <ref>` end by calling
`print_parent_preview`, which walks the touched task's ancestors and — when the
touched task is *closed* (e.g. a `done` story, exactly the `todo s28` case in the
bug report) — has no open ancestor and falls into its "show all open roots"
branch. The result is the entire open task tree instead of the TODO list. The
fix: after the confirmation, show the *updated TODO list* (using `list --todo`
semantics), with the touched task highlighted, and — recognising this is a
house-wide gap — introduce a uniform action-report format that all
report-and-preview commands will eventually adopt. `s26t19` is the pilot; the
rest migrate under a follow-up task.

## Decisions

- **Render the updated TODO list, not the parent preview** — replace
  `print_parent_preview` in `cmd_todo`/`cmd_untodo` with a TODO-list render using
  the same active/finished semantics as `list --todo` (active-only by default;
  `All tasks finished!` when every pin is closed). This is "the TODO list" the
  title refers to. *Rejected: a bespoke minimal render (raw pins, no filtering) —
  a third inconsistent rendering mode, same reasoning s26t18 used.*
- **`untodo` renders the same updated TODO list, symmetrically** — resolves the
  task's own TBD. Both commands share one mental model ("edit the TODO list, then
  show it"). *Rejected: showing non-todo open tasks after untodo — reintroduces
  the "show everything open" sprawl this bug removes.*
- **Highlight the touched task(s) in both commands** — `todo` and `untodo` both
  highlight what they just changed. `untodo` shows the just-detached task even
  when it would otherwise be filtered out, so the user sees it now carries **no**
  `(todo)`/`(tX)` marker. Highlight and marker are complementary (one draws the
  eye, the other conveys state).
- **Suppress the open-tasks fallback except when `untodo` empties the list** —
  the empty→"list all open leaf tasks" fallback in `list --todo` is exactly the
  sprawl this bug kills, so suppress it for the normal path. But when `untodo`
  removes the *last* pin, print a distinct "that was the last one — TODO list now
  empty" message **and** show the open-tasks fallback (it helps the user pick
  what's next), still highlighting the touched task. *Rejected: always
  suppressing (loses the helpful next-step list when the list truly empties);
  always reusing `list --todo` verbatim (dumps the open tree on the common path).*
- **`todo`-ing a closed task mirrors `list --todo`'s all-finished state** — when
  the post-add active set is empty, print `All tasks finished!` and show the
  closed pins, with the touched closed task highlighted among them. Honest state,
  keeps add/list consistent.
- **`untodo` on a task pinned only via an ancestor warns specifically** — the
  TODO list stores task *ids*; a pinned parent renders its open descendants
  nested, but those descendants are not in `todo_ids`, so `remove_todo` returns
  `False`. On that `False`, walk `get_parent` against `load_todo_ids`; if a pinned
  ancestor exists, warn naming it ("in TODO via pinned parent … — untodo … to
  remove it"), leave the task in `todo_ids`, and highlight **both** the child and
  the pinned ancestor. Only when *no* pinned ancestor exists keep the plain
  `(was not in todo)`.
- **Uniform action-report format (house-wide convention)** — precede the render
  with a report block: an `<Action>:` header (`Adding to TODO:` /
  `Removing from TODO:`) then one bullet per requested ref,
  `- <id>: <title>[  (<outcome>)]`. The trailing `(outcome)` is shown **only when
  it deviates** from the header's implied action — successful add/remove get no
  annotation; `(already in todo)`, `(was not in todo)`, the via-parent warning,
  and the last-one/empty note are annotated. Drops the old per-ref
  `Task X added to todo` sentences. *Rejected: freeform per-command echo lines
  (contract 3 of ADR 0004) — inconsistent across commands.*
- **Reusable reporter as a config object** — mirror `ShowTaskConfig`/`print_tree`:
  `ActionReportConfig(action=...)` with `add_item(ref, title, *, outcome=None)`,
  rendered by `print_action_report(config)`. Callers build the config across the
  batch loop, then render once.
- **Printing helpers print only; callers own JSON** — `print_action_report` and
  the TODO render are pure text (silent under `--json-output`, like `print_tree`).
  The command emits `task_refs` JSON itself via `console.append_context`. JSON
  output stays exactly as today (`task_refs` acks only; no task tree). *Rejected:
  the reporter emitting `task_refs` context — conflicts with the print-only
  contract that `print_tree` already follows.*
- **Module split** — the general reporter lives in `_print_utils.py` (genuinely
  general). The todo-specific render + highlight overlay lives in a **new**
  `_todo_view.py`, which also absorbs `_collect_todo_tasks` moved out of
  `_view_commands.py`; both `_view_commands.py` and `_todo_commands.py` import it.
  `tasker/todo.py` stays pure domain (no console). *Rejected: putting the todo
  render in `_print_utils.py` — too specific for the general utils module.*
- **Batch semantics** — compute all requested refs together; print one report
  block (multiple bullets) then one rendered result; the empty/all-finished and
  last-one-removed decisions are made once from the *final* `todo_ids`, not
  per-ref.
- **Amend ADR 0004 (do not write a new ADR)** — 0004
  (`commands-speak-json-recent-and-preview`, still `proposed`) already owns "how
  commands report"; add the action-report format there as a contract, note it
  supersedes contract 3's freeform echo, mark `todo`/`untodo` as first adopter,
  and reference the follow-up migration task. *Rejected: a new ADR 0005 —
  fragments one convention across two records.*

## Open questions

- None.

## Out of scope

- Migrating the other report-and-preview commands (`done`/`cancel`/`reset`/`move`/
  `order`/`unarchive`/`new`/`add`) to the action-report format — deferred to a
  dedicated follow-up task; s26t19 is the pilot that establishes the format.
- Any `CONTEXT.md` glossary change — "action report" is an implementation/reporting
  convention (belongs in ADR 0004), not a domain term.
- Emitting the rendered TODO tree as JSON — JSON consumers use
  `list --todo --json-output`.

## Subtasks

- [x] [s26t1901](s26t1901-amend-adr-0004-with-the.md): Amend ADR 0004 with the action-report format
- [ ] [s26t1902](s26t1902-reusable-action-report-reporter-deep.md): Reusable action-report reporter (deep module)
- [ ] [s26t1903](s26t1903-fix-todo-output.md): Fix `todo` output
- [ ] [s26t1904](s26t1904-fix-untodo-output.md): Fix `untodo` output
