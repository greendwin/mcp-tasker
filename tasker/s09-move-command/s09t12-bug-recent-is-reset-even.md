---
id: s09t12
slug: bug-recent-is-reset-even
status: pending
---

# BUG: recent is reset even on qNN reference

recent should never be reset by its own reference (i.e if I use q01, this resolved ref should never override q)

TBD: what to do in case when we use --parent ADDR, when ADDR should be saved to recent? after ALL operations!
TBD: recent should never be updated during operations!

```
$ td move q01 q02 -p s23t01
Task s23t0104 moved under s23t01-task-1
Renamed tasks:
  s24t01 → s23t0104

s23t01: Task 1
  - s23t0104: Task 100 <<< (q)
Error: Cannot resolve task reference 's23t010402'
```
