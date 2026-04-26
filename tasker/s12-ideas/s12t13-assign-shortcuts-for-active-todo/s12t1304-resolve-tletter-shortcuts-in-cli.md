---
id: s12t1304
slug: resolve-tletter-shortcuts-in-cli
status: pending
---

# Resolve `t<letter>` shortcuts in CLI

Rename `_resolve_recent` → `_resolve_shortcut` in `resolve.py` and add a `t<letter>(NN)*` branch.

## Behaviors to test (CLI integration via `assert_invoke`)

1. `task show ta` resolves to the first active todo task.
2. `task show tc` resolves to the third active todo task.
3. `task show ta01` resolves to the first child of the task that `ta` points to.
4. `task show ta0102` resolves through nested child paths (mirrors `q0102`).
5. Unknown letter (e.g. `tz` when only 3 active todos) → `TaskValidateError`.
6. `t<letter>` resolution does NOT update the recent task (verify `q` afterwards points to whatever it was before).
7. Existing `q`/`p`/`qNN` references continue to work unchanged.

## Notes
- Add the `t<letter>` branch in the renamed `_resolve_shortcut`.
- Update the dispatch check (currently `task_ref.startswith(("p", "q"))`) to also accept the `t<letter>` prefix.
- `save_recent_for_refs` already filters non-direct refs — no change needed there.
