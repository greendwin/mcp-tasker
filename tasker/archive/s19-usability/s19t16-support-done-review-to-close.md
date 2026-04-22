---
id: s19t16
slug: support-done-review-to-close
status: done
---

# Support done --reviewed to close in-review tasks

Add `--reviewed` flag (short alias `--rev`) to the `done` command as pure sugar for closing all currently in-review tasks in one go.

## Semantics

`done --reviewed [refs...]` is equivalent to running `done <explicit-refs> <all-non-archived-in-review-refs>` as a **union**. The flag just expands into additional refs before the existing `cmd_done_task` loop runs.

- No deduplication logic beyond what current `done` already does (if a ref appears twice, the second pass prints "was already finished" — same as today).
- No confirmation prompt. Reviewers can undo with `reset`, and the rest of tasker's CLI doesn't prompt either.
- No MCP equivalent. Agents going through MCP should close tasks explicitly by ref for auditability; this flag is ergonomic sugar for a human clearing a review queue.

## Discovery

Walk every root from `repo.list_root_tasks(archived=False)` via `walk_tasks`, collect tasks with `status == IN_REVIEW`. Archived trees are skipped — touching in-review tasks under an archived root would be surprising and likely stale.

## Edge cases

- **Empty bulk** — `done --reviewed` with zero in-review tasks and no explicit refs → exit 0 with an info message like "No in-review tasks to close". Empty queue is the normal steady state, not an error.
- **Refs + empty queue** — `done --reviewed s01` where `s01` is `in-progress` and nothing else is in-review → closes `s01` anyway. Explicit refs are unconditional; the in-review set is additive and may legitimately be empty.
- **`--force` interaction** — composes independently. In-review tasks are leaf-only by construction, so `--force` only ever matters for explicit nonleaf refs passed alongside `--reviewed`.

## Touch points

- `src/tasker/cli/_status_commands.py` — add the `--reviewed`/`--rev` option to `cmd_done_task`, expand the ref list before the existing loop.
- Tests in the matching `tests/cli/` file: empty bulk, bulk-only, union with explicit refs, union where explicit ref overlaps the in-review set, archived tasks are skipped, interaction with `--force` on a nonleaf explicit ref.
- No MCP changes, no `DESIGN.md` changes (behavior-level sugar, not a new concept).
