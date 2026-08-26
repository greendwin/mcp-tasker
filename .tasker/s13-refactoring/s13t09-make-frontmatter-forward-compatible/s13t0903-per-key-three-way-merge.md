---
id: s13t0903
slug: per-key-three-way-merge
status: pending
---

# Per-key three-way merge of frontmatter extras

## Goal

`tasker resolve` merges task files whose branches touched *different* unknown
frontmatter keys cleanly; the same key changed differently on both sides emits a
standard conflict block containing each side's YAML dump of that key.

## Decisions & constraints

- Merge extras per top-level key using the existing `_merge_field` three-way
  logic (base/ours/theirs), comparing parsed YAML values by deep equality.
  Rejected: whole-blob merge — two tools annotating different keys concurrently
  is the core use case and must merge cleanly.
- Key set is the union of base/ours/theirs keys: added-on-one-side merges in;
  deleted-on-one-side + unchanged-on-other deletes; delete-vs-modify conflicts.
- Merged extras emit in the same position as slice s13t0902 (after owned keys),
  ours-side key order first, then theirs-only keys.
- Conflict block content: `key: <safe_dump of that key's value>` per side,
  reusing `_conflict_block` / `_MergeComposer.append_conflict`.

## Edge cases

- No base (both sides added the same key with equal values → merged; different
  values → conflict).
- Nested value changed deep inside a mapping — still a whole-key conflict (no
  recursive merge).
- One side has no extras at all.
- Merged output with conflicts must still be re-parseable after the user
  resolves markers.

## Key files

- `src/tasker/merge.py` — `merge_task_file`, new per-key extras merge
- `tests/test_merge_model.py`, `tests/test_merge_task_file.py`

## Acceptance criteria

- Different-keys-changed merges produce no conflict and keep both annotations.
- Same-key-both-changed produces a conflict block with each side's YAML dump.
- Owned-field merge behavior is unchanged.
- `uv run tox` passes (all environments).
