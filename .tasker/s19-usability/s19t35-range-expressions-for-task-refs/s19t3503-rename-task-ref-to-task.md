---
id: s19t3503
slug: rename-task-ref-to-task
status: pending
---

# Rename task_ref to task_id below the resolution boundary

## Goal

Every parameter below `resolve_ref` speaks `task_id`, so a surviving `task_ref` deep in the call graph is a grep-able defect.

## Decisions & constraints

- The three concepts are now distinct (ADR 0005, CONTEXT.md): a **task id** is the canonical identity and the only currency below the resolution boundary; a **task ref** is user input at the CLI/MCP boundary and may resolve to many ids; a **filename stem** is a filesystem concern.
- `task_ref` survives **only** on CLI argument declarations and MCP tool schemas. It cannot be abolished entirely: `q`, `p03`, `pp0102`, `ta`, `bugs` and range expressions demonstrably are not ids, so the ref concept is real — it just stops existing below the boundary.
- *Rejected: dropping "ref" entirely* and calling user input "task id" too — breaks down immediately on `q`/`bugs`/`s19t10-15`.
- `TaskValidateError`'s `task_ref` field is **audited case by case, not blindly renamed**. It legitimately carries a raw user ref when raised from shortcut resolution (`_resolve_shortcut`, `_resolve_by_name`, where the input is `q`/`bugs` and no id exists yet) and an id everywhere else (`_task_loader.py:319,330`, `_move_task.py:38,49,223`). Decide per raise site; the JSON payload key should match what is actually carried.
- Pure rename, deliberately isolated from behavioural change so slices 4 and 5 review cleanly. No functional change in this slice.

## Edge cases

- `repo.resolve_ref(task_id)` on `TaskRepo`/`TaskLoader` (`_task_loader.py:63`) takes an already-normalised id, *not* a user ref, despite the name — this is exactly the ambiguity the rename exists to kill. It should become something like `get_task(task_id)`, distinct from `resolve.resolve_ref`.
- `try_resolve_ref` (`_organize_commands.py:517,523`) has the same problem.
- `unarchive_root_task_impl(repo, task_ref)` (`_move_task.py:233`) receives an id.
- `parse_task_ref` / `ParsedRef.task_ref` operate on ids *and* filename stems, not user refs — name them for what they parse.
- `resolve.ResolvedRef.task_ref` genuinely holds the original user ref (used by `save_recent_for_refs` to decide whether it was a direct ref) — that one keeps the name.

## Key files

- `src/tasker/resolve.py`, `src/tasker/parse.py`
- `src/tasker/repo/_task_loader.py`, `src/tasker/repo/_task_repo.py`, `src/tasker/repo/_move_task.py`
- `src/tasker/exceptions.py`
- `src/tasker/cli/*.py`, `src/tasker/mcp/*.py` (boundary declarations keep `task_ref`)
- `docs/agents/task-tracker.md` documents MCP `task_ref:` params — boundary, so unchanged

## Acceptance criteria

- `grep -rn "task_ref" src/tasker` returns hits only in: CLI `typer.Argument`/`Option` declarations, MCP tool signatures, `ResolvedRef.task_ref`, and shortcut-resolution error raises.
- `repo.resolve_ref` no longer shares a name with `resolve.resolve_ref`.
- No behavioural change: the full test suite passes with only mechanical test updates.
- `uv run tox` clean across all environments.
