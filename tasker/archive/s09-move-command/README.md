---
id: s09
slug: move-command
status: done
---

# Support move command 

Attache subtree to another task or make it a separate story

## Subtasks

- [x] s09t01: Support move <ref> --parent <ref>
- [x] s09t02: Support move <ref> --root
- [x] s09t03: Recalc task ids, show list of task renames (in --json-output too)
- [x] s09t04: Remove old files (need to store original file, current heuristics is not enough)
- [x] s09t05: Refactor move code - store original files in Loader (see s13)
- [x] s09t06: BUG: moving inline task to root does not create a task
- [x] [s09t07](s09t07-task-degradation.md): Task degradation
- [x] s09t08: Accept multiple args, move all tasks either to root or attach to a parent
- [x] s09t09: BUG: detach from deep nested parent fails to remove multiple ancestor directories
