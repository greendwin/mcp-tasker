---
id: s19t28
slug: support-move-id-for-tasks
status: done
---

# Support move --id for tasks rename

## Context

After a git merge, two tasks can collide on the same id, and there's no in-tool way to renumber one. `tasker move --id <new-id>` lets a user rename a task to any free, canonically-valid id. The new id determines placement (re-home by implied parent), descendants are relabeled recursively, and shorthand input is accepted. Scoped to repos that still load cleanly — hard dup-id states are fixed on disk first.

## Decisions

- **`--id` re-homes by implied parent** — the new id determines tree position: `s05t03→s05t07` relabels in place, `→s09t01` re-parents under `s09`, `→s07` converts to root; children relabel recursively. *Rejected: pure-relabel-same-parent-only — strictly less general, would need a parallel code path instead of reusing move machinery.*
- **`--id` joins the mutual-exclusivity group** — exactly one of `--parent`/`--root`/`--delete`/`--id`; it implies its own placement so the others are redundant/nonsensical. *Rejected: tolerating a consistent `-p`+`--id` — no information gained for the extra branch + test matrix.*
- **Single task ref only with `--id`** — a concrete target id can belong to one task; >1 ref errors early.
- **`--editor` allowed with `--id`** (opens renamed task at new id); `--delete` stays incompatible.
- **Shorthand input, normalized to canonical** — accept `s1t5`→`s01t05` and pasted canonical `s05t0302`; even/odd disambiguation; reject a trailing slug and non-root levels >99 (pair-splitter depends on 2-digit levels). *Rejected: canonical-only (too strict, user wanted shorthand); accepting `s5` alongside `s05` (collides under int-based scanner).*
- **Extract public `normalize_task_id` in `parse.py`** — reuses the existing even/odd logic from `resolve.py._normalize_direct_ref`/`_normalize_shortcut_digits`; `_normalize_direct_ref` delegates to it; strict mode *raises* (no silent passthrough/slug-stripping) for `--id`. *Rejected: a `strict=` flag on `parse_task_ref` — keeping its lenient contract isolated is cleaner.*
- **Free + parent-exists checks via `repo.resolve_ref`** — parent must resolve (subtask targets); target must be a clean "not found" to be free; resolved-or-ambiguous = occupied. The loader's active→archive fallback covers archived automatically.
- **Idempotency pre-check** — target == current id → no-op reusing "already in the requested location", skipping the uniqueness check and move machinery.
- **Thread `new_id` through `move_task_impl`** — bypass its two no-op short-circuits (`ref.parent_id == new_parent.id` and `_convert_to_root`'s `is_root_task_id`) and auto-id generation when set; `repo.move_task` gains a pass-through `new_id`. *Rejected: a dedicated `rename_task_impl` — chose to extend the existing function.*
- **Orchestration in `cmd_move_task`** — normalize, resolve implied parent, run free/parent/idempotency checks CLI-side, mirroring how `--parent` is resolved before `repo.move_task`. `move_task_impl` stays mechanical (trusts validated inputs).
- **Reuse existing self/descendant cycle guards** — `new_parent.id == task.id` ("under itself") and `_is_descendant_of` ("under its descendant") already fire on the `--id` path; no new validation.
- **CLI-only** — no MCP `rename_task` this round. *Rejected adding it: would pull orchestration down into `repo` for no current need.*
- **Message by outcome** — root target → reuse `moved to root`; different parent → reuse `moved under {parent}`; same parent → new `renamed to {new_id}`; idempotent → existing line. Shared `Renamed tasks:` block follows in all non-idempotent cases.
- **`--id` option spec** — `Optional[str]`, no short alias, no autocompletion (a completer would suggest occupied ids), conflict-resolution help text.

## Open questions

- None outstanding.

## Out of scope

- **Ambiguity-tolerant source addressing** (separate follow-up task) — repairing a genuinely collided repo (two `s07-*` dirs → "Ambiguous"; subtask dup → "registered twice" at load) by resolving the source via exact `id-slug`. `move --id` operates only on a loadable repo; hard dup-id states are fixed on disk first.
- MCP `rename_task` tool.

## Subtasks

- [x] [s19t2801](s19t2801-normalizetaskid-deep-module.md): Normalize_task_id deep module
- [x] [s19t2802](s19t2802-thread-newid-through-move-mechanics.md): Thread new_id through move mechanics
- [x] [s19t2803](s19t2803-move-id-cli-wiring.md): Move --id CLI wiring
- [x] [s19t2804](s19t2804-document-move-id-in-designmd.md): Document move --id in DESIGN.md
