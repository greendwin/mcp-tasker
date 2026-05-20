---
id: s19t2702
slug: extend-padding-to-tsegment-s1t1
status: pending
---

# Extend padding to t-segment (s1t1, s02t2, multi-level, ambiguity)

Apply `_normalize_shortcut_digits` to the t-segment digit run in `_normalize_direct_ref`. Cases:

- `s1t1`, `s01t1`, `s1t01` → `s01t01`
- `s1t0102` → `s01t0102` (multi-level even run, no change)
- `s12t34` → unchanged passthrough
- `s1t102` → raises `TaskValidateError` (odd-length t-run > 1)

Add tests for each, plus a guard test that `parse_task_ref("s1")` still raises (locks in the Q2 boundary).
