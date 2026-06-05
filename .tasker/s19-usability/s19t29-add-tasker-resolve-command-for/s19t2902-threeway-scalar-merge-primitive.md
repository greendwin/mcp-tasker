---
id: s19t2902
slug: threeway-scalar-merge-primitive
status: pending
---

# Three-way scalar merge primitive

## Goal

A generic three-way merge helper for single values: given base/ours/theirs, return the merged value or signal a conflict.

## Decisions & constraints

- Conservative policy: one side changed → take it. Both changed to same value → take it. Both changed differently → conflict.
- Used by later slices for frontmatter fields (status, slug) and prose blobs (title, description, extra_sections).

## Edge cases

- Base is None (new file in both branches)
- Value unchanged on both sides
- Both changed to the same thing (no conflict)

## Key files

- `src/tasker/merge.py` (new)

## Acceptance criteria

- `merge_scalar(base="A", ours="A", theirs="B")` → `"B"`
- `merge_scalar(base="A", ours="B", theirs="A")` → `"B"`
- `merge_scalar(base="A", ours="B", theirs="C")` → conflict
- `merge_scalar(base="A", ours="A", theirs="A")` → `"A"`
- `merge_scalar(base="A", ours="B", theirs="B")` → `"B"` (both agree)
