---
id: s11
slug: tasks-archivation
status: pending
---

# Tasks archivation

add 'archive' command that moves complete task to 'planning/archive'

## Subtasks

- [x] s11t01: Make sure that task is done
- [x] s11t02: Support --force option (mark tasks as cancelled)
- [x] s11t03: TBD: reference tasks in archive
- [x] s11t04: TBD: unarchive task
- [x] ~~s11t05: TBD: unarchive by adding to a task (maybe we should unarchive root task first)~~
- [x] s11t06: Add 'unarchive' command
- [x] s11t07: 'new' command must count archived task IDs on creation, so 'unarchive' will never collide
- [x] s11t08: Actions on archived task must report that task is archived; note: dont load archived tasks, store ids of archived root tasks, its enought
- [x] s11t09: Support multiple arguments on both `arch` and `unarch`
- [x] s11t10: Unarchive task when trying to 'add' to archived story
- [x] s11t11: Allow to move archived task (reference story itself) to non-archived parent
- [x] s11t12: Trying to attach any task (either archived or unarchived) to an archived task must unarchive it
- [x] s11t13: BUG: when archiving with force, parent status would be CANCELLED regardless of existing done tasks
- [x] s11t14: Support --closed - archive all closed stories
- [ ] [s11t15](s11t15-support-loading-archived-tasks-in.md): Support loading archived tasks in TaskRepo
- [ ] [s11t16](s11t16-rework-autoanarchive-logic.md): Rework auto-anarchive logic
