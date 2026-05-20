---
id: s26t06
slug: bug-list-todo-should-not
status: done
---

# BUG: list --todo should not show non-todo opened tasks

Example:
```
$ t list --todo
s25: [x] AI Pipeline
  - s25t02: [x] Support manager dashboard (todo)
s26: Bugs
  - s26t02: [x] BUG: (q) can reference deleted task, it should not fail in this case (todo)
  - s26t03: List --arch should not show non-archived tasks until asked
  - s26t04: On actions like 'add' recently closed should not be shown
```
