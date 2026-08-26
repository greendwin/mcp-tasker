---
id: s13t1008
slug: migrate-archive-with-dimmed-archived
status: pending
---

# Migrate archive with dimmed archived rendering

## Goal

`archive` emits an `Archiving:` action report and then a remaining-open-roots
overview in which the just-archived stories still appear, rendered **dimmed**.
Per-ref confirmation sentences and the "Forcibly cancelled subtasks:" listing
are gone. `.recent` stays untouched.

## Decisions & constraints

- Report: bullets per requested root (dedup by resolved id), outcomes
  `(already archived)` and `--force` cascade as `(forced N open subtasks)` per
  the standard pattern; the forced subtask enumeration lives only in
  `forced_task_ids` JSON now.
- Overview (design review outcome): reuse `untodo`'s empty-list landscape shape
  — `list_open_leaf_tasks` + `print_parents_with_opened` — and include the
  just-archived stories so the user sees where they went. Rejected: report-only
  output (user preferred seeing the post-archive landscape).
- **Dimmed archived style**: add an archived branch to `format_task_list_item`
  analogous to the `task.deleted` red branch, but `bright_black`/dim — archived
  is "moved out of view", not "destroyed".
- `.recent` still not updated (accepted ADR 0004 deviation — archiving moves a
  story out of the active view). ADR text amendment lands in the final slice.
- `--closed` sweep and root-only validation unchanged; errors
  (non-root, open without `--force`) still raise before any report.
- JSON contract unchanged: `task_refs`, `already`, `forced_task_ids`.

## Edge cases

- `--closed` with no closed stories: nothing archived — no empty report header
  (reporter already skips empty configs); decide/keep a sensible message.
- Archiving the last open story: overview falls back like untodo's empty case
  (archived stories shown dimmed, no open roots).
- Mixed already-archived + forced + plain in one invocation.
- Duplicate refs; explicit ref also matched by `--closed` sweep (already
  deduped via `used` set — keep one bullet).

## Key files

- `src/tasker/cli/_organize_commands.py` — `cmd_archive_task`
- `src/tasker/cli/_print_utils.py` — `format_task_list_item` archived style
- `tests/test_archive_commands.py`

## Acceptance criteria

- Human output: `Archiving:` + bullets, then roots overview with archived
  stories dimmed among remaining open roots.
- No `.recent` write; JSON tests pass unchanged.
- Duplicate-ref test: one bullet, one JSON entry, action applied once.
- `uv run tox` passes (all environments).
