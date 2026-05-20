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

## Example

~ ⌚ 10:30:19
$ t list
╭─────────────────────────────────────────────────────────── Traceback (most recent call last) ────────────────────────────────────────────────────────────╮
│ in func:2                                                                                                                                                │
│                                                                                                                                                          │
│ /home/greendwin/.local/pipx/venvs/mcp-tasker/lib/python3.10/site-packages/tasker/cli/_common.py:78 in get_task_repo                                      │
│                                                                                                                                                          │
│    75                                                                                                                                                    │
│    76                                                                                                                                                    │
│    77 def get_task_repo() -> TaskRepo:                                                                                                                   │
│ ❱  78 │   tasker_dir = discover_tasker_dir()                                                                                                             │
│    79 │   return TaskRepo(tasker_dir)                                                                                                                    │
│    80                                                                                                                                                    │
│    81                                                                                                                                                    │
│                                                                                                                                                          │
│ /home/greendwin/.local/pipx/venvs/mcp-tasker/lib/python3.10/site-packages/tasker/layout.py:60 in discover_tasker_dir                                     │
│                                                                                                                                                          │
│    57 │   │   return user_dir                                                                                                                            │
│    58 │                                                                                                                                                  │
│    59 │   # 3. not found                                                                                                                                 │
│ ❱  60 │   raise TaskerNotFoundError                                                                                                                      │
│    61                                                                                                                                                    │
│    62                                                                                                                                                    │
│    63 def init_tasker_dir(project_root: Path | None = None) -> Path:                                                                                     │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
TaskerNotFoundError: Tasker directory not found. Run 'tasker init' or 'tasker init --user' to initialize.
