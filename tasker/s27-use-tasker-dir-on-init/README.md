---
id: s27
slug: use-tasker-dir-on-init
status: done
---

# Create '.tasker' dir on 'init'

Switch project initialization to create `.tasker/` instead of `tasker/`, while keeping full backward compatibility for projects that already use the legacy name.

## Rules

- **Project dir**: new name is `.tasker/`. Legacy `tasker/` is still discoverable.
- **User-level dir** (`--user`): stays `tasker/` under XDG / LOCALAPPDATA — already inside a hidden/app-data parent.
- **Discovery**: walk parents from cwd; at each level check `.tasker/` first, then `tasker/`; first hit wins. Nearer dir always beats farther one. User-level `tasker/` is the final fallback.
- **`init` on an already-initialized dir**: if a legacy `tasker/` exists at the target root and is a valid tasker dir, do nothing and return that path. Do not create a parallel `.tasker/`. No auto-migration.
- **Detection (`is_tasker_dir`)**: unchanged — same `.recent` / `# tasker` gitignore-header markers apply to both names.

## Out of scope

- No ADR / CONTEXT.md change (reversible, no new vocabulary).
- No migration command and no auto-rename of legacy dirs.
- No changes to the in-dir `.gitignore` contents or to any project-root `.gitignore`.

## Tracer-bullet slices

1. Discovery recognizes `.tasker/`.
2. `init` creates `.tasker/` in clean dirs; no-op when legacy `tasker/` exists.
3. Discovery precedence (same-level + nearer-wins) pinned by tests.
4. User-level `--user` still creates/discovers `tasker/` (regression guard).
5. Update `DESIGN.md` and `README.md`.

## Subtasks

- [x] [s27t01](s27t01-discovery-recognizes-tasker.md): Discovery recognizes `.tasker/`
- [x] [s27t02](s27t02-init-creates-tasker-noop-on.md): `init` creates `.tasker/`; no-op on legacy
- [x] [s27t03](s27t03-pin-discovery-precedence-rules.md): Pin discovery precedence rules
- [x] [s27t04](s27t04-userlevel-dir-stays-tasker-regression.md): User-level dir stays `tasker/` (regression guard)
- [x] [s27t05](s27t05-update-designmd-and-readmemd.md): Update DESIGN.md and README.md
