---
id: s26t12
slug: when-failing-resetting-extra-error
status: done
---

# When failing resetting - extra Error: 1

Example:
```bash
$ t reset s27
Task s27-use-tasker-dir-on-init has subtasks — its status is managed automatically
Reset its subtasks first, or use --force

Non-pending subtasks:
  - s27t01: [x] Discovery recognizes `.tasker/`
  - s27t02: [x] `init` creates `.tasker/`; no-op on legacy
  - s27t03: [x] Pin discovery precedence rules
  - s27t04: [x] User-level dir stays `tasker/` (regression guard)
  - s27t05: [x] Update DESIGN.md and README.md
Error: 1   <<<--- should not be there!
```
