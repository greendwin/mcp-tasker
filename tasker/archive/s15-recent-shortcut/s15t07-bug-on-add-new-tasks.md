---
id: s15t07
status: done
---

# BUG: on add new tasks overrides 'recent'

Example:
```bash
$ t show q
[ ] Tasks archivation
...
Subtasks:
  [x] s11t01: Make sure that task is done
  [x] s11t02: Support --force option (mark tasks as cancelled)
...

$ t add q "unarchive task"
Task s11t10 added to s11-tasks-archivation

# <<- here q referenced s11t09
$ t add q "allow to move"
Task s11t0901 added to s11t09-support-multiple-arguments-on-both

$ t add q "trying to attach"
Task s11t0902 added to s11t09-support-multiple-arguments-on-both
