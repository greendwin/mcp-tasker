---
id: s26t07
slug: valid-error-when-tasker-dir
status: done
---

# Valid error when tasker dir not found

**Problem:** `TaskerNotFoundError` (and other `TaskerError`s from DI-resolved dependencies like `get_task_repo`) are raised outside the `catching_output` wrapper because TyperDI resolves `Depends()` before the decorated function body runs. This produces ugly tracebacks instead of clean `Error: <message>` output.

**Fix:**
1. Convert `catching_output` decorator on `OutputContext` into a `catching_errors()` context manager
2. Create `_TaskerGroup(TyperGroup)` that wraps `invoke()` with `console.catching_errors()`
3. Pass `cls=_TaskerGroup` to the `TyperDI` app so all commands (and DI resolution) are covered
4. Remove `@console.catching_output` from all individual commands
5. Raise `SystemExit(1)` after handling `TaskerError` (preserving exception chaining)
