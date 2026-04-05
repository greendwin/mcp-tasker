---
id: s11t16
slug: rework-autounarchive-logic
status: done
---

# Rework auto-unarchive logic

Unarchive only when adding a new task or moving tasks with non-closed status.
Otherwise -- just load and edit archived tasks as before.
When attaching a subtree -- it becomes archived unless it has non-closed tasks.

## Subtasks

- [x] ~~[s11t1601](s11t1601-refactor-further-tasks.md): Refactor further tasks~~
- [x] [s11t1602](s11t1602-add-already-archivedunarchived-logic.md): Add "already archived/unarchived" logic
- [x] [s11t1603](s11t1603-merge-archive-and-move-modules.md): Merge archive and move modules
- [x] [s11t1604](s11t1604-add-helpers-to-iterate-over.md): Add helpers to iterate over tasks tree
- [x] [s11t1605](s11t1605-make-reportxxx-methods-jsonoutput-agnostic.md): Make _report_xxx methods json_output agnostic
- [x] s11t1606: Fix: validate slug on loading a task - it can be illformed, normalize it to slug-name form
