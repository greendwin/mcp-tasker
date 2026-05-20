---
id: s09t11
slug: merge-previewed-tasks-on-multiple
status: done
---

# Merge previewed tasks on multiple move ops

Note: preview block with (q) should be shown only once

```
$ td move s23t0104 s23t0201 s23t0105 -p s24
Task s24t01 moved under s24-test-story-ii
Renamed tasks:
  s23t0104 → s24t01

s24: Test story II
  - s24t01: Task 100 <<< (q)

Task s24t02 moved under s24-test-story-ii
Renamed tasks:
  s23t0201 → s24t02

s24: Test story II
  - s24t01: Task 100
  - s24t02: Task 200 <<< (q)

Task s24t03 moved under s24-test-story-ii
Renamed tasks:
  s23t0105 → s24t03

s24: Test story II
  - s24t01: Task 100
  - s24t02: Task 200
  - s24t03: Task 300 <<< (q)
```
