---
id: s19t27
slug: pad-single-digits-in-direct
status: done
---

# Pad single digits in direct task refs (s1 → s01, s02t2 → s02t02)

Extend the single-trailing-digit padding rule (currently only on `q`/`p`/`t<letter>` shortcuts) to direct `s...t...` refs.

After this change, both segments accept single-digit shorthand:

- `s1` → `s01`
- `s1t1`, `s01t1`, `s1t01` → `s01t01`
- `s1t0102` → `s01t0102`
- `s1t102` → ambiguous (odd-length t-run > 1)

**Design decisions** (from grill of 2026-05-20):

- Normalize in `resolve.py` via a new `_normalize_direct_ref` helper, invoked from `resolve_ref` before the `_is_direct_ref` dispatch. `parse_task_ref` in `parse.py` stays strict.
- Reuse `_normalize_shortcut_digits` per digit segment so the "single digit pads, odd > 1 is ambiguous" rule stays in one place.
- Preserve trailing `-slug` suffix on direct refs (e.g. `s1-foo` → `s01-foo`).
- Generalize the error message to `Ambiguous digits in task ref {ref!r}` and use it for both shortcut and direct-ref paths.
- Update DESIGN.md (extend existing padding sentence) and README.md line 246 to mention direct refs.

## Subtasks

- [x] [s19t2701](s19t2701-tracer-pad-ssegment-only-s1.md): Tracer: pad s-segment only (s1 → s01) end-to-end
- [x] [s19t2702](s19t2702-extend-padding-to-tsegment-s1t1.md): Extend padding to t-segment (s1t1, s02t2, multi-level, ambiguity)
- [x] [s19t2703](s19t2703-preserve-trailing-slug-suffix-on.md): Preserve trailing -slug suffix on direct refs
- [x] [s19t2704](s19t2704-generalize-error-message-and-update.md): Generalize error message and update DESIGN.md + README.md
