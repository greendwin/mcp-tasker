---
id: s26t18
slug: open-tasks-list-should-be
status: in-progress
---

# Open tasks list should be grouped

When `tasker done` (or `done --rev`) finds nothing to close, it prints an
"Open tasks:" hint. Today that hint is a flat, leaf-only list with no story
context. The goal is to render it grouped like `tasker list` / `list --todo`:
each root story as a header with its open descendants nested beneath, so the
fallback matches the rest of the CLI's tree output.

## Decisions

- **Reuse `print_tree` for the rendering** — build a `ShowTaskConfig` from the
  open roots and call `print_tree`, producing the same story-header + nested
  open-subtree output as `tasker list` with no args. Gives order-aware sorting
  and todo/recent markers for free. *Rejected: a bespoke "flat list with a story
  header line" renderer — it would be a third inconsistent rendering mode.*
- **Show the full open subtree via `ShowChildrenMode.SHOW_OPENED`** — render
  intermediate open non-leaf tasks too, not just leaves. Parity with
  `list`/`--todo` is the whole point; intermediate open tasks are real work and
  their context helps. *Rejected: preserving the old leaf-only semantics.*
- **Include only roots with open work; suppress the header when none** — feed
  `print_tree` only the roots that actually contain an open task, and print the
  `Open tasks:` header solely when that set is non-empty. Preserves the existing
  guards (no section when nothing is open; closed tasks never appear). The
  existing open-leaf predicate stays as the "is there open work / which roots"
  selector. *Rejected: calling the full `list` code path verbatim — it shows
  closed roots as bare headers and always prints, breaking both guards.*
- **Keep todo/recent markers** — accept whatever `print_tree` emits (`(todo)`,
  `(ta)`, `(q)`/`(p)`), matching `list`/`--todo`. *Rejected: adding a suppression
  flag just for this caller.*
- **Local private helper** — put the grouped render in a private helper in the
  status-commands module (one caller); reuse the existing `ShowTaskConfig` /
  `print_tree` primitives. The other flat "Open subtasks:" listings (non-leaf
  finish failure, cancel) stay flat — they are single-parent contexts.
- **JSON output unchanged** — the section stays human-only; `print_tree` emits no
  structured context, matching today's behavior. *Rejected: emitting an
  `open_tasks` context array for `list` parity — scope creep, no consumer.*

## Edge cases

- **Nothing open** — the whole `Open tasks:` header must be absent (guard:
  `test_done_empty_without_open_tasks_skips_open_section`).
- **Closed tasks** — done/cancelled tasks and closed roots never appear.
- **Childless open story** — an open root that is itself a leaf (no subtasks)
  shows as a single root line.
- **Deep/intermediate open non-leaf tasks** — now rendered (previously skipped),
  since `SHOW_OPENED` walks the full open subtree.
- **Multiple open stories** — each renders as its own header block with its own
  nested open tasks, in `sorted()` (order-then-id) order.

## Key files

- `src/tasker/cli/_status_commands.py` — the `done`-empty branch (~lines
  342-349) and `_iter_open_leaf_tasks` (~line 387); add the private grouped-print
  helper here.
- `src/tasker/cli/_print_utils.py` — reuse `ShowTaskConfig`, `ShowChildrenMode`,
  `print_tree` (no changes expected).
- `tests/test_done_commands.py` — rewrite `test_done_empty_skips_nonleaf_tasks`;
  add a multi-story grouping test; keep the three guard tests.

## Acceptance criteria

- With one open story + open leaf, `tasker done` (nothing to close) prints the
  story header **and** the leaf indented (`  - `) beneath it.
- With two open stories each holding an open leaf, each story header precedes its
  own indented leaf (grouped, not interleaved).
- When nothing is open, no `Open tasks:` header appears.
- Closed tasks/roots never appear in the listing.
- `uv run tox` passes (all environments), including the three retained guards.

## Open questions

- None.

## Out of scope

- Grouping the other flat listings (non-leaf finish-failure "Open subtasks:", the
  cancel equivalent) — single-parent contexts, left flat.
- Any structured/JSON payload for the open-tasks section.
- No `CONTEXT.md` term or ADR — "grouped" just describes the existing tree
  rendering; the change is an easily-reversible parity fix.
