---
id: s19t3501
slug: ids-are-what-we-print
status: pending
---

# Ids are what we print and emit

## Goal

`tasker done s19t01` prints `Task s19t01 done` rather than `Task s19t01-my-slug done`, and `--json-output` emits `task_id` / `task_ids` whose values are task ids.

## Decisions & constraints

- `Task.ref` is renamed `Task.filename_stem`. It keeps its current `<id>-<slug>` value and stays a property — we rejected removing it and having filesystem callers build the stem via `build_task_ref(task.id, task.slug)`, which scatters filename construction across the loader for no gain.
- Filesystem call sites keep the slug-bearing form; display and JSON switch to `task.id`. The slug remains a filesystem concern and nothing else.
- Printing ids is a **fix, not a new decision**: ADR 0004 already requires that "the authoritative result reporting — the rename listing, the preview tree, and the `--json-output` payload — must reference tasks by their final ids". The current `Task [blue]{task.ref}[/blue]` lines were already out of line with it.
- JSON keys rename outright to `task_id` / `task_ids`. *Rejected: keeping `task_ref`/`task_refs` with id values, which enshrines exactly the confusion this work removes; and emitting both as deprecated aliases, which doubles every payload to protect a contract nobody has pinned.* There is no persisted schema and no consumer outside agents reading fresh output, so compat cost is near zero.
- Scope is output only. Input parsing still accepts slug refs after this slice — that is slice 2.

## Edge cases

- Inline tasks have `slug is None`, so `filename_stem` already falls back to the bare id — the rename must not change that fallback.
- `_common.py:148` (`Unarchiving {root_task.ref} automatically`) is a user-facing message and switches to id; `repo/_utils.py:114,130,132` and `_task_loader.py:265,278,395,426` are filesystem paths and must keep the stem.
- `_task_loader.py:360` has a comment noting it deliberately uses the *original* `tt.task_ref` because `task.ref` can be changed from the file — preserve that distinction under the new name.
- `exceptions.py:41` currently passes `task.id` under a `task_ref` JSON key; align it with the new key naming.
- `merge.py:112` builds a stem via `build_task_ref` for a different model — check whether it is affected.

## Key files

- `src/tasker/base_types.py` (`Task.ref` property, `build_task_ref`)
- `src/tasker/cli/_status_commands.py`, `_create_commands.py`, `_edit_commands.py`, `_view_commands.py`, `_organize_commands.py`, `_common.py`
- `src/tasker/exceptions.py`
- `src/tasker/repo/_utils.py`, `src/tasker/repo/_task_loader.py`
- `tests/test_action_report.py`, `tests/test_start_review_commands.py`, `tests/test_done_commands.py`, `tests/test_create_commands.py`, `tests/test_edit_commands.py`, `tests/test_view_commands.py`

## Acceptance criteria

- `tasker start <id>` on a task with a slug prints the bare id in its result line.
- `tasker done <id> --json-output` emits a `task_ids` key containing ids; no `task_refs` key remains anywhere in CLI output.
- `tasker view <id> --json-output` emits `task_id`, not `task_ref`.
- Task files and directories are still created and renamed with `<id>-<slug>` names — no filesystem naming changes.
- `Task.ref` no longer exists; `Task.filename_stem` returns the bare id for inline tasks.
