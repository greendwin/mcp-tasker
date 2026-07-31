---
id: s28t01
slug: order-field-model-parse-render
status: pending
---

# Order field: model, parse, render (round-trip)

**Goal**
The `order` field persists through disk end-to-end: a task file with `order: <n>` in its front matter parses into `Task.order`, and rendering writes it back out — but only when set. A plain/unordered task is byte-unchanged (no `order:` line). This is the tracer bullet for the persistence layer; no display or mutation behavior yet.

**Decisions & constraints**
- Add `order: int | None = None` to the strict `Task` model (`extra="forbid"` — the field must be declared, not passed as an unknown kwarg).
- Front-matter key is `order:` (integer). Serialize only when `order is not None` — None omits the line entirely, so existing files and plain inline/unordered tasks stay byte-identical.
- Add `order` to the `_parse_content` front-matter allowlist (it currently raises `Unknown front-matter field` for anything unrecognized).
- Field name is `order`, not `rank` (names the sequence-of-work intent; aligns with the future `order` verb / `order_tasks` tool). Rejected `rank`/`priority` (importance/score connotations).

**Edge cases**
- `order: 0` and negative values: parse as-is (values are internal; sort tolerates anything). No validation beyond "is an int".
- Malformed `order:` value (non-integer) → `TaskValidateError` consistent with other front-matter parse errors.
- Round-trip stability: loading a file with `order:` then rendering must reproduce the line; loading one without must not add it.

**Key files**
- `src/tasker/base_types.py` (Task model)
- `src/tasker/parse.py` (`_parse_content` allowlist + int parse)
- `src/tasker/render.py`, `src/tasker/templates/task.md.j2` (emit `order:` when set)

**Acceptance criteria**
- A file with `order: 2000` parses to `Task.order == 2000`.
- Rendering a task with `order=2000` emits exactly one `order: 2000` front-matter line; rendering a task with `order=None` emits none.
- A file without `order:` round-trips byte-identically (no line added).
- An unknown front-matter field still raises; `order` no longer does.
