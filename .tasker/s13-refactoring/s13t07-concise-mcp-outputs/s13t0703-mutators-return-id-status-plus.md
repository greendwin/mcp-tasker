---
id: s13t0703
slug: mutators-return-id-status-plus
status: pending
---

# Mutators return {id, status} plus affected on force

**Goal:** all mutating MCP tools stop echoing caller-supplied data and return the minimal structured result.

**Decisions & constraints:**
- `create_task`, `edit_task`, `start/review/reset/cancel/finish_task` return structured `{id, status}` (full enum status string, e.g. `"in-review"`). The resolved `id` is genuinely new info when the caller passed a shortcut/slug; title/description are pure echo. Rejected: returning full `TaskInfo`; a bare status or confirmation string (loses the resolved id, less machine-clean than tiny JSON).
- `reset/cancel/finish_task` add `affected: [ids]` ONLY when `force` actually cascaded a status change to subtasks -- surfaces the side effect (the whole point of `force`) without echoing full child objects. Absent/empty when nothing cascaded.
- Mutations stay STRUCTURED (not text) even though reads went text/markdown: a confirmation carries one or two machine-relevant facts (resolved id, new status, maybe affected ids); a tiny JSON object conveys them unambiguously. Text is for scannable multi-row/long-body output, not a 2-field ack.
- Resolve the deferred model-shape question: use ONE result model with an optional `affected` field (default empty/absent) -- keeps the schema uniform across all mutators.
- Cascade detection: capture the open subtask ids before the repo call and diff against post-state (or use whatever the repo `reset/cancel/finish` methods expose) so `affected` is non-empty only when children actually changed status.
- Introduce the result model (e.g. a new `src/tasker/mcp/_result.py`). `create_task` / `edit_task` / status methods stop using `TaskInfo` / `TaskPreview`.
- Preserve existing side-effect behavior: `cancel_task` / `finish_task` still call `save_closed_refs` only on a real (not already-closed) transition.

**Edge cases:**
- `force=True` with no open subtasks -> empty/absent `affected`.
- `force=False` -> no `affected`.
- Cancel/finish an already-closed task -> no double `save_closed_refs` (preserve current guard).
- `edit_task` -> status unchanged but still returned in `{id, status}`.
- Shortcut/slug ref -> the returned `id` is the resolved canonical id.

**Key files:** `src/tasker/mcp/_create_methods.py`, `src/tasker/mcp/_status_methods.py`, new `src/tasker/mcp/_result.py`, `tests/test_mcp_create.py`, `tests/test_mcp_edit.py`, `tests/test_mcp_status.py`.

**Acceptance criteria:**
- `create_task(...)` returns `{id, status}` only -- no title/description echo.
- `finish_task(story, force=True)` returns `{id, status, affected: [child ids]}`; with `force=False` (or no cascade) `affected` is absent/empty.
- `start_task("ta")` (a shortcut) returns the resolved canonical id in `id`.
