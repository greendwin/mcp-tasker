---
id: s27t01
slug: discovery-recognizes-tasker
status: done
---

# Discovery recognizes `.tasker/`

Extend `discover_tasker_dir` so it finds a `.tasker/` directory in addition to the legacy `tasker/`.

## Scope
- `layout.py`: at each parent level, check `.tasker/` then `tasker/`; return first valid hit.
- `is_tasker_dir` unchanged.
- `init` still creates legacy `tasker/` (changed in next slice).

## Test first
- Hand-craft a `.tasker/` with a `.recent` marker; assert `discover_tasker_dir` returns it.
- Existing legacy-`tasker/` discovery tests still pass.

## Demo
`mkdir -p .tasker && touch .tasker/.recent && tasker list` works.
