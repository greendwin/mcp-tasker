---
id: s19t17
slug: rework-lastclosed-to-clossed-flag
status: done
---

# Rework implicit closed display to explicit `--closed` flag

Replace the implicit "show closed batch in `list`" behavior with an explicit `tasker list --closed` flag backed by a rolling history.

## Storage

- New file `tasker/.closed`: plain text, one task ID per line, append-only, 30-entry cap
- On re-close of an existing ID: remove old entry, append to end (dedup + move-to-newest)
- `.closed` seeded into `init_tasker_dir` gitignore body next to `.recent`/`.todo`
- `ensure_gitignore_entry(repo.root, CLOSED_FILE)` called on first write (same pattern as `.todo`)
- `tasker/.recent` reverts to plain text (just the recent task ID); legacy JSON format silently ignored on read, never written — no migration

## Append semantics (`done`/`cancel`, CLI + MCP)

- Append only user-specified refs to `.closed`
- Drop the forced-children appends (`_status_commands.py:286,387` and MCP equivalent in `_status_methods.py`)
- `--reviewed`-pulled tasks count as user-specified (they already flow through `resolved_tasks`)
- `already_finished`/`already_cancelled` tasks still skipped
- No new MCP tool for querying closed history

## Read semantics (`load_closed_tasks`)

- Read newest-first
- Reach deeper until N live IDs resolve or file exhausted
- Collect stale IDs encountered along the way; rewrite `.closed` with them removed (lazy smart prune — only prune what we tried)

## CLI: `list --closed`

- `--closed` is a bool flag. Always shows up to 5 most-recent closed tasks.
- No count override for now — Typer dropped support for the optional-int pattern (`is_flag=False, flag_value=N`); if we need `-n N` later we can revisit.
- Mutually exclusive with `--archived`, `--todo`, and positional `task_refs` (error on combine)
- Compatible with `--all` (uses `ShowChildrenMode.SHOW_ALL`)
- Renders each closed task exactly like a positional `task_ref`: same parent line, same markers, same children mode
- Newest-first display order
- `list` without `--closed` no longer implicitly shows closed tasks (remove `load_closed_tasks` call at `_view_commands.py:104-106`)
- JSON output: closed tasks go into the same `"tasks"` key (consumers filter by `status`)

## Deferred

- No `closed_time` attribute on tasks — append-order in `.closed` is sufficient
- No new MCP surface for closed history
- No runtime count override; default 5 is hardcoded

## Docs

- `DESIGN.md` `### View tasks`: add `list --closed` entry
- `DESIGN.md`: add `.closed` mention parallel to `.todo` description
- `README.md` lines 102-106: add `tasker list --closed`

## Tests (all via `assert_invoke`, no mocks)

CLI shape:
1. `list` no args → no longer shows closed tasks
2. `list --closed` → last 5 closed, newest-first
3. `list --closed` with <5 in `.closed` → shows what's there
4. `list --closed` with empty `.closed` → "No tasks to show"
5. `list --closed --all` → full subtree (covers `done --force` case)
6. `list --closed` + `--archived` → error
7. `list --closed` + `--todo` → error
8. `list --closed` + positional refs → error

History semantics:
9. `done s05t01` then `done s05t02` → both in `.closed`, newest first
10. `done s05 --force` with children → only `s05` in `.closed`, not forced children
11. `done s05t01 s05t02 s05t03` → all three in typed order
12. `done --reviewed` → in-review tasks appear in `.closed`
13. Reset then re-done → dedupe + move to newest
14. 30-entry cap → oldest evicted
15. Lazy prune: stale IDs skipped on read and removed from file; keeps reaching for N live
16. Empty / missing `.closed` file → treated as empty history

Storage format:
17. `.recent` plain-text round-trip; legacy JSON silently ignored
18. `.closed` gitignore entry auto-added on first write

MCP parity:
19. MCP `done`/`cancel` apply same append-semantics

## Storage

- New file `tasker/.closed`: plain text, one task ID per line, append-only, 30-entry cap
- On re-close of an existing ID: remove old entry, append to end (dedup + move-to-newest)
- `.closed` seeded into `init_tasker_dir` gitignore body next to `.recent`/`.todo`
- `ensure_gitignore_entry(repo.root, CLOSED_FILE)` called on first write (same pattern as `.todo`)
- `tasker/.recent` reverts to plain text (just the recent task ID); legacy JSON format silently ignored on read, never written — no migration

## Append semantics (`done`/`cancel`, CLI + MCP)

- Append only user-specified refs to `.closed`
- Drop the forced-children appends (`_status_commands.py:286,387` and MCP equivalent in `_status_methods.py`)
- `--reviewed`-pulled tasks count as user-specified (they already flow through `resolved_tasks`)
- `already_finished`/`already_cancelled` tasks still skipped
- No new MCP tool for querying closed history

## Read semantics (`load_closed_tasks`)

- Read newest-first
- Reach deeper until N live IDs resolve or file exhausted
- Collect stale IDs encountered along the way; rewrite `.closed` with them removed (lazy smart prune — only prune what we tried)

## CLI: `list --closed`

- `Optional[int]` option with `is_flag=False, flag_value=5`:
  - `--closed` → 5
  - `--closed 10` → 10
  - omitted → None (normal list)
- Mutually exclusive with `--archived`, `--todo`, and positional `task_refs` (error on combine)
- Compatible with `--all` (uses `ShowChildrenMode.SHOW_ALL`)
- Renders each closed task exactly like a positional `task_ref`: same parent line, same markers, same children mode
- Newest-first display order
- `list` without `--closed` no longer implicitly shows closed tasks (remove `load_closed_tasks` call at `_view_commands.py:104-106`)
- JSON output: closed tasks go into the same `"tasks"` key (consumers filter by `status`)

## Deferred

- No `closed_time` attribute on tasks — append-order in `.closed` is sufficient
- No new MCP surface for closed history

## Docs

- `DESIGN.md` `### View tasks`: add `list --closed` / `list --closed N` entry
- `DESIGN.md`: add `.closed` mention parallel to `.todo` description
- `README.md` lines 102-106: add `tasker list --closed`

## Tests (all via `assert_invoke`, no mocks)

CLI shape:
1. `list` no args → no longer shows closed tasks
2. `list --closed` → last 5 closed, newest-first
3. `list --closed 10` / `list --closed=10` → last 10
4. `list --closed` with <5 in `.closed` → shows what's there
5. `list --closed` with empty `.closed` → "No tasks to show"
6. `list --closed --all` → full subtree (covers `done --force` case)
7. `list --closed` + `--archived` → error
8. `list --closed` + `--todo` → error
9. `list --closed` + positional refs → error

History semantics:
10. `done s05t01` then `done s05t02` → both in `.closed`, newest first
11. `done s05 --force` with children → only `s05` in `.closed`, not forced children
12. `done s05t01 s05t02 s05t03` → all three in typed order
13. `done --reviewed` → in-review tasks appear in `.closed`
14. Reset then re-done → dedupe + move to newest
15. 30-entry cap → oldest evicted
16. Lazy prune: stale IDs skipped on read and removed from file; keeps reaching for N live
17. Empty / missing `.closed` file → treated as empty history

Storage format:
18. `.recent` plain-text round-trip; legacy JSON silently ignored
19. `.closed` gitignore entry auto-added on first write

MCP parity:
20. MCP `done`/`cancel` apply same append-semantics
