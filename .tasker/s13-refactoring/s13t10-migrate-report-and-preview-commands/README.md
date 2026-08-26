---
id: s13t10
slug: migrate-report-and-preview-commands
status: pending
---

# Migrate report-and-preview commands to the action-report format

## Context

Follow-up to s26t19, which piloted the uniform action-report format
(`<Action>:` header + `- <id>[  (<outcome>)]` id-only bullets, deviation-only
annotation) on `todo`/`untodo`, added the reusable `ActionReportConfig` /
`print_action_report` reporter in `_print_utils.py`, and documented the format
in ADR 0004. This task migrates every remaining report-and-preview command to
that format so all commands report uniformly. Scope was expanded during design
review: `start`, `review`, and `archive` migrate too (their per-ref confirmation
prose is exactly what the format supersedes); only `edit` keeps its text
preview.

## Scope

- `done`, `cancel`, `reset`, `start`, `review` (status commands)
- `move`, `order`, `unarchive`, `archive` (organize commands)
- `new`, `add` (create commands)

## Decisions

- **`start`/`review` switch to the tree preview** — replace
  `print_task(preview=True)` with the highlighted task-tree preview
  (`print_parents_with_opened`): the user wants to see where the status changed
  in the tree, not reread the task body. ADR 0004's accepted-deviation entry for
  the lighter preview shrinks to `edit` only.
- **`archive` gets a report + remaining-roots overview** — `Archiving:` report,
  then the open-roots landscape (reuse the `list_open_leaf_tasks` +
  `print_parents_with_opened` shape from `untodo`'s empty-list path) with the
  just-archived stories still visible, rendered **dimmed** (new archived style
  in `format_task_list_item`, analogous to the deleted-red branch). `.recent`
  stays untouched (accepted deviation).
- **Forced cascades collapse to a count** — the requested ref's bullet is
  annotated e.g. `(forced 3 open subtasks)`; the individual forced tasks stay
  visible via preview highlights and the `forced_task_ids` JSON. *Rejected: a
  bullet per forced subtask (repeats ids a third time).*
- **`move`: renames are bullet outcomes** — mode-specific header (`Moving under
  s02:` / `Moving to root:` / `Renaming:` / `Deleting:`); bullets carry final
  ids annotated `(was <old-id>, renamed N subtasks)` when applicable; the human
  `Renamed tasks:` listing is removed (descendants appear only as the count);
  the `renames` JSON stays complete including descendants. The `--id` self-move
  early return folds into the normal flow — bullet `(already in place)` plus
  `.recent` and preview — fixing its latent ADR 0004 contract-1/3 gap.
- **`order`: anchor lives in the header** — `Ordering after <anchor>:` /
  `Ordering at front:` / `Clearing order:`; the anchor never gets a bullet
  (annotating a non-deviation is against the format). `--rest`-swept siblings
  get real bullets mirroring their `task_refs` JSON entries — they receive the
  action itself, unlike descendant renames. Cross-parent adoption renames use
  the `(was …)` outcome pattern.
- **`new`/`add` migrate for uniformity** — anchor-in-header pattern (`Created:`
  / `Adding under <parent>:`) with one bullet (the new id); singular `task_ref`
  JSON unchanged. *Rejected: keeping one-sentence confirmations (reintroduces a
  per-command special case).*
- **Duplicates are ignored** (ADR 0004): requested refs dedupe by resolved task
  id before processing, first-occurrence order — one bullet, one `task_refs`
  JSON entry, one application; never a deviation annotation. Covered with tests
  per command, mirroring the `todo`/`untodo` duplicate-ref tests.
- **JSON contracts unchanged** — the reporter is print-only; each command keeps
  emitting its own `task_refs`/`task_ref`/`renames`/`forced_task_ids` context.
- **ADR 0004 updates** — adopter note reflects adoption; accepted deviations
  amended (text preview: `edit` only; `archive`: keeps no-`.recent`, gains
  report + roots overview).

## Out of scope

- `edit` — keeps its `print_task` text preview (showing the edited text is the
  point).
- `add-many` — stays a bulk primitive with no per-task preview.
- Any behavioural change beyond the above (no new flags, no changed preview
  trees elsewhere).

## Acceptance criteria

- Every in-scope command emits the uniform action report before its preview.
- `start`/`review` preview via the highlighted task tree; `archive` shows the
  remaining-roots overview with dimmed archived stories.
- Each migrated command ignores duplicate refs per ADR 0004, with covering
  tests.
- Existing JSON-output tests for those commands pass unchanged (except the
  `move --id` self-move path, which now also updates `.recent` and previews).
- ADR 0004's adopter note and deviations are updated as decided.
- `uv run tox` passes (all environments).

## Subtasks

- [ ] [s13t1001](s13t1001-action-report-for-done.md): Action report for done
- [ ] [s13t1002](s13t1002-action-report-for-cancel.md): Action report for cancel
- [ ] [s13t1003](s13t1003-action-report-for-reset.md): Action report for reset
- [ ] [s13t1004](s13t1004-rework-start-action-report-plus.md): Rework start: action report plus tree preview
- [ ] [s13t1005](s13t1005-rework-review-action-report-plus.md): Rework review: action report plus tree preview
- [ ] [s13t1006](s13t1006-migrate-move-renames-as-bullet.md): Migrate move: renames as bullet outcomes
- [ ] [s13t1007](s13t1007-migrate-order-anchor-in-header.md): Migrate order: anchor in header, real bullets for rest
- [ ] [s13t1008](s13t1008-migrate-archive-with-dimmed-archived.md): Migrate archive with dimmed archived rendering
- [ ] [s13t1009](s13t1009-migrate-unarchive.md): Migrate unarchive
- [ ] [s13t1010](s13t1010-migrate-new.md): Migrate new
- [ ] [s13t1011](s13t1011-migrate-add-finalize-adr-0004.md): Migrate add; finalize ADR 0004
