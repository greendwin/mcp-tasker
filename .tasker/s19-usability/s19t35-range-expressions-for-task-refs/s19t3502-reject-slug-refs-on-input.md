---
id: s19t3502
slug: reject-slug-refs-on-input
status: pending
---

# Reject slug refs on input

## Goal

`tasker view s19t35-my-slug` fails with a message naming the id to use instead, and shell completion offers `s19t35` rather than the slug form.

## Decisions & constraints

- Hard break, no deprecation shim. *Rejected: warn-and-accept for one minor release* — the warning path requires retaining the slug-stripping code, which is precisely the dual-mode parser this work exists to delete; it would defer the refactoring that motivates the change. *Rejected: silently stripping non-numeric tails forever*, which leaves the ref/id ambiguity in place.
- The error must be targeted, not generic. Detect a `-<non-numeric tail>` and say *"Slug refs are no longer accepted — use `s19t35`"*, quoting the id the user should have typed. A bare `Invalid task ref: '…'` does not tell someone why something that worked yesterday stopped.
- Completion emits bare ids. The task title is already the completion description, so the human-readable context the slug provided is not lost. *Rejected: appending the slug to the description* — redundant with the title.
- Batch-aware completion is explicitly out of scope (see the parent task's Out of scope, and the separate follow-up task).
- This is a semver-visible break on a `1.8.1` package: flag it for an explicit "Breaking" line at the next `/prepare-release`.
- `_resolve_by_name` (matching root-task slugs, e.g. `tasker add bugs`) is a **separate mechanism** and must keep working — it resolves *by* slug rather than accepting a slug tail on an id.

## Edge cases

- `parse_task_ref` strips the tail at `parse.py:58`; `normalize_task_id` strips it via the `(?:-.*)?` group at `parse.py:90`. Both need to stop accepting it, but `parse_task_ref` is also called on *filename stems* read from disk (`detect_task_type`, `_task_loader.py:81`), where the slug tail is legitimate and required — those call sites need a stem-parsing path that still accepts it.
- A ref whose tail is all digits (`s19t10-20`) must not be caught by the slug-detection branch — that is a range expression once slice 4 lands, and before then should not produce a misleading "slug refs" error.
- Names that look sluggy but are root-task name matches (`bugs`, `usability`) contain no `s<digits>` prefix and must route to `_resolve_by_name` unchanged.
- Completion currently scans only root tasks and their direct subtasks; do not change that scope here.

## Key files

- `src/tasker/parse.py` (`parse_task_ref`, `normalize_task_id`, `detect_task_type`)
- `src/tasker/resolve.py` (`_is_direct_ref`, `resolve_ref`)
- `src/tasker/cli/_common.py` (`complete_task_ref`)
- `tests/test_parse.py`, `tests/test_cli_common.py`, `tests/test_resolve_name.py`, `tests/test_cli_errors.py`

## Acceptance criteria

- `tasker view s19t01-any-slug` errors with a message containing both "slug" and the bare id `s19t01`.
- `tasker view s19t01` still resolves.
- `tasker add bugs "..."` (root-task name match) still resolves.
- Completion for incomplete `s19` returns bare ids only, with titles as descriptions.
- Task files on disk with `<id>-<slug>` names still load — stem parsing is unaffected.
