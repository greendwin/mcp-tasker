---
id: s19t2701
slug: tracer-pad-ssegment-only-s1
status: done
---

# Tracer: pad s-segment only (s1 → s01) end-to-end

Minimal end-to-end slice: add `_normalize_direct_ref` in `resolve.py` that pads just the s-segment digit run, wire it into `resolve_ref` before `_is_direct_ref` dispatch, and prove `s1` resolves like `s01` through a single test. No t-segment handling, no slug, no error wording changes yet.
