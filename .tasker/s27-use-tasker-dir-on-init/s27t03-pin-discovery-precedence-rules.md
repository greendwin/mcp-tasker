---
id: s27t03
slug: pin-discovery-precedence-rules
status: done
---

# Pin discovery precedence rules

Lock in the precedence rules with explicit tests so future refactors don't regress them.

## Scope
- No production code change expected if slices 1–2 are correct; this slice is mostly tests.
- Adjust `layout.py` only if a test reveals a gap.

## Test first
- Same level: both `.tasker/` and `tasker/` present → `.tasker/` wins.
- Cross-level: nearer legacy `tasker/` in cwd beats farther `.tasker/` in a parent.
- Cross-level: nearer `.tasker/` in cwd beats farther legacy `tasker/` in a parent.
- No project dir anywhere → falls back to user-level `tasker/`; raises `TaskerNotFoundError` if absent.
