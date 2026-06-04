---
id: s19t2801
slug: normalizetaskid-deep-module
status: done
---

# Normalize_task_id deep module

## Goal

A pure, public `normalize_task_id(raw)` in `parse.py` that expands user id input to canonical form (`s1t5` → `s01t05`), with `resolve.py._normalize_direct_ref` delegating to it.

## Decisions & constraints

- `normalize_task_id` is **pure expansion only** — pad single digits, strip a trailing slug, passthrough unchanged on non-match. No `strict` mode: the `--id` strict validation (reject slug / reject non-match) is handled by the CLI caller (s19t2803), not here.
- Extract the even/odd shorthand logic currently in `resolve.py._normalize_shortcut_digits` into one tested place in `parse.py` (renamed `_normalize_id_digits`, co-located with `parse_task_ref`); `resolve.py` imports it back for its 5 shortcut call sites.
- `_normalize_direct_ref` collapses to `return normalize_task_id(task_ref)` — preserving its current contract exactly.
- Odd-length t-run >1 still raises "Ambiguous digits" (inherent to expansion — an odd run can't be split into 2-digit levels). The 2-digit-pair grammar makes a non-root level >99 unrepresentable, so that's enforced by the even/odd rule, not a separate check.
- Output is the canonical stored form: single `t`, 2-digit level pairs.
- *Rejected: a `strict=` flag on `normalize_task_id` — strictness belongs outside the expansion helper.*

## Edge cases

- `s1t5` → `s01t05`; `s05t0302` kept; `s1t12` → `s01t12`.
- odd>1 (`s1t123`) → raises ("Ambiguous digits").
- trailing slug → stripped (`s01-foo` → `s01`); non-match → passthrough (`q` → `q`).
- multi-`t`/even-run input falls through to the canonical-paste path.

## Key files

- `src/tasker/parse.py`, `src/tasker/resolve.py`
- tests: `tests/test_parse.py`, `tests/test_cli_common.py`

## Acceptance criteria

- `normalize_task_id("s1t5")` returns `"s01t05"`; `normalize_task_id("s05t0302")` returns `"s05t0302"`.
- `normalize_task_id("s01-foo")` returns `"s01"`; `normalize_task_id("q")` returns `"q"`.
- `normalize_task_id("s1t123")` raises `TaskValidateError` ("Ambiguous digits").
- Existing `_normalize_direct_ref` / resolve / shortcut tests still pass (lenient behavior unchanged).
