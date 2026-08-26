---
id: s13t0902
slug: preserve-unknown-frontmatter-keys-via
status: pending
---

# Preserve unknown frontmatter keys via extra on Task

## Goal

A task file with unknown frontmatter keys — including nested YAML mappings and
lists — parses without error, and re-rendering emits those keys intact after the
owned keys, in first-seen order. The "Unknown front-matter field" error is
removed.

## Decisions & constraints

- New `extra: dict[str, Any] = {}` field on `Task` (`base_types.py`); all
  non-owned keys from the parsed mapping land there. Data-level fidelity:
  values survive as parsed YAML data; comments/formatting do not (ADR 0005).
- Emission: after the owned fields, before the closing `---`, via
  `yaml.safe_dump(extra, sort_keys=False)` — insertion order preserved. A key
  positioned above `status:` in a source file normalizes below the owned keys
  on first rewrite, then is byte-stable (same philosophy as `## Subtasks`
  always moving last). Rejected: dumping the whole mapping as one YAML document
  (cosmetic churn on all existing files, owned-field rendering leaves the
  template).
- No reserved names: keys that look internal (`title:`, `extended:`,
  `subtasks:`) are preserved silently like any other extra. A future tasker
  that claims a key migrates its value out of `extra` itself.
- Files without extras must render byte-identically to today.

## Edge cases

- Nested structures (`metadata:` with an indented block) round-trip as data.
- Non-string scalar values (ints, bools, dates) survive a load→dump cycle.
- Extras survive the full repo pipeline: parse → in-memory edit (status change,
  edit_task) → flush_to_disk.
- Empty `extra` emits nothing (no stray document markers or blank lines).
- safe_dump line wrapping / quoting normalization is acceptable; second render
  must be byte-stable.

## Key files

- `src/tasker/parse.py` — `_parse_content` / `_ParsedContent` / `parse_task`
- `src/tasker/base_types.py` — `Task.extra`
- `src/tasker/render.py`, `src/tasker/templates/task.md.j2` — emission
- `tests/test_parse.py`, `tests/test_mcp_render.py`, `tests/test_task_repo.py`

## Acceptance criteria

- Unknown keys (flat and nested) survive parse→render byte-stably from the
  second render on.
- Extras survive a status change + flush round-trip on disk.
- A file without extras renders byte-identically to the pre-change output.
- `uv run tox` passes (all environments).
