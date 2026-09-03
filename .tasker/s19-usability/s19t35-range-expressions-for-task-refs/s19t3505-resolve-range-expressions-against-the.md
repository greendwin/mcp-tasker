---
id: s19t3505
slug: resolve-range-expressions-against-the
status: pending
---

# Resolve range expressions against the task tree

## Goal

`tasker done s19t10-15,17` closes those tasks and reports one action-report bullet per resolved id.

## Decisions & constraints

- **Anchor rule.** The base names an anchor; groups enumerate that anchor's children. This makes shortcuts fall out for free from the existing `qNN`/`pNN` semantics documented in DESIGN.md:

  | Expression | Anchor | Selects |
  |---|---|---|
  | `s19t10-15` | `s19` | `s19t10`…`s19t15` |
  | `s19t3502-05` | `s19t35` | its children 02–05 |
  | `s01-05` | root level | `s01`…`s05` |
  | `q10-15` | recent task | children 10–15 of recent |
  | `p10-15` | parent of recent | siblings 10–15 of recent |
  | `pp01..` | grandparent of recent | all its children from 01 |
  | `ta02-04` | the `ta` todo task | its children 02–04 |

- **Filter, do not generate.** Expansion filters the anchor's *actual* children, so interior gaps are skipped silently — sibling numbering is sparse in practice (this repo's own `s19` jumps 29→31 and is missing 01 and 04). But **both written endpoints must exist**, which catches the fat-finger `s19t10-99` and the stale-id paste at no legitimate cost. An omitted endpoint on an open range is nothing to validate. *Rejected: generate-and-require-all, defeated by any real tree; and filter-with-unchecked-endpoints, which silently over-selects.*
- **Ascending id order**, not repo sibling order. `Task.__lt__` sorts by order key first, so expanding by it would make `tasker order s19t10-15` a circular no-op that reaffirms whatever order already exists instead of normalising to id sequence. Ascending id also makes report bullets predictable and diffable.
- **Status-blind, archive-aware.** Done and cancelled siblings are included — the action report's `(already done)` annotation is exactly how those get reported, so filtering them would strip the report of its job. But a range only enumerates the anchor's own archive partition: archived roots are hidden from `list` by default and must not be swept into a mutation the user cannot see. For subtask ranges this is a no-op since archived-ness is inherited from the root; it only bites at root level. *Rejected: command-sensitive expansion, which would make one expression mean different sets per verb — the one thing a selection language must never do.*
- **Resolution becomes 1→many everywhere.** The user's mental model is "a ref may name several tasks", full stop; a grammar legal in `done` but a syntax error in `view` is a rule you memorise per command. Single-ref call sites enforce arity explicitly with a counting error: *"`s19t10-15` selected 6 tasks, expected 1"*. *Rejected: rejecting range syntax at parse time on single-ref parameters; and fanning `view` out over a range, which makes the `--json-output` shape depend on the ref, cutting against ADR 0004's uniform-payload contract.*
- **One bullet per resolved id.** Expansion is invisible in output: `done s19t10-15` reads exactly as if six ids were typed. This keeps ADR 0004's `(outcome)` deviation annotations working, which a grouped bullet could not — three of six already done has no single outcome. ADR 0004 has already been amended with this clarification.
- Dedup by resolved id in first-occurrence order per ADR 0004, so `s19t10-15,12` yields `12` once.
- MCP is **not blocked** — range expressions still resolve if passed. Only the documentation posture differs (slice 6).

## Edge cases

- `q10-15` when `.recent` is unset must give the existing "Recent task was not set yet" error, not a range error.
- `p`-family anchors walk up via `parse_task_ref(...).parent_id`; `pp` on a root task has no grandparent.
- Root-level ranges (`s01-05`) enumerate the non-archived partition via `list_root_tasks(archived=False)`; naming an archived root as an endpoint should error clearly rather than silently excluding it.
- An open range on an anchor with no children resolves to the empty set — decide whether that is an error or a no-op report.
- `save_recent_for_refs` computes the common ancestor of direct refs; a range under one anchor collapses to that anchor, which is consistent with typing the ids out. Shortcut-based ranges (`q10-15`) are not direct refs and must not move `.recent`, matching current behaviour.
- `tasker order s19t10-15` must receive the tasks in ascending id order.
- `resolve_user_refs` already dedups by id — extend rather than duplicate that logic.

## Key files

- `src/tasker/resolve.py` (`resolve_ref`, `resolve_user_refs`, `_resolve_shortcut`, `_is_direct_ref`)
- the grammar module from slice 4
- `src/tasker/repo/_task_repo.py`, `src/tasker/repo/_task_loader.py` (sibling enumeration, archive partitions)
- `src/tasker/cli/_view_commands.py`, `_edit_commands.py`, `_create_commands.py`, `_organize_commands.py` (single-ref arity sites)
- `src/tasker/mcp/_status_methods.py` (`_mutate_task` arity site)
- `tests/test_resolve_commands.py`, `tests/test_action_report.py`, `tests/test_done_commands.py`, `tests/test_order_commands.py`, `tests/test_archive_commands.py`

## Acceptance criteria

- `tasker done s19t10-15,17` closes exactly the existing siblings in 10–15 plus 17, and the action report lists one bullet per resolved id, ascending.
- A range with a gap (`s19t27-32` where 30 is absent) succeeds and skips the gap.
- A range whose written endpoint does not exist errors, naming the missing endpoint.
- `s19t10-15,12` produces six bullets, not seven.
- Already-done members are included and annotated `(already done)`, not silently dropped.
- `q10-15`, `p10-15`, `ta02-04` and `s01-05` all resolve per the anchor table.
- `tasker view s19t10-15` errors with a message stating the selected count and that one was expected.
- A root-level range does not select archived roots.
- `tasker order s19t10-15` receives them in ascending id order.
