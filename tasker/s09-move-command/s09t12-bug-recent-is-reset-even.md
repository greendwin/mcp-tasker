---
id: s09t12
slug: bug-recent-is-reset-even
status: done
---

# BUG: recent is reset even on qNN reference

* recent should never be reset by its own reference (i.e if I use q01, this resolved ref should never override q)
* in ALL operations, recent should be updated after finishing all operations (especially when multiple tasks are passed)
* when multiple tasks are passed -- prefer to choose their common ancestor

```
$ td move q01 q02 -p s23t01
Task s23t0104 moved under s23t01-task-1
Renamed tasks:
  s24t01 → s23t0104

s23t01: Task 1
  - s23t0104: Task 100 <<< (q)
Error: Cannot resolve task reference 's23t010402'
```
