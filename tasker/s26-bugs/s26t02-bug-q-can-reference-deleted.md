---
id: s26t02
slug: bug-q-can-reference-deleted
status: pending
---

# BUG: (q) can reference deleted task, it should not fail in this case

Example

```
~/tasker on  main! ⌚ 23:54:17
$ td move q --delete
Task q deleted

s27: Test story <<< (q)

~/tasker on  main! ⌚ 23:54:24
$ td list
Error: Task 's27' not found
```
