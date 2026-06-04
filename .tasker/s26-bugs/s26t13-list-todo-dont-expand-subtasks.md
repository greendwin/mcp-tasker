---
id: s26t13
slug: list-todo-dont-expand-subtasks
status: done
---

# List --todo don't expand subtasks

Note following output. There are subtasks under s06t18, but `list --todo` does not expand them.

```
# greendwin @ ecimbalyuk in ~/repo-skills on git:main o [0:30:51]
$ t todo s06t16 s06t18 s06t19
Task s06t16-autoattach-untracked-skills-on-update already in todo
Task s06t18-update-specific-source already in todo
Task s06t19-allow-to-edit-source-skills already in todo

s06: Usability (q)
  - s06t06: Add 'skills diff' command
    - s06t0601: Extract shared helpers from _merge.py
    - s06t0602: Basic diff command for tracked modified skill
    - s06t0603: Edge cases: not modified, added/deleted files,
errors
  - s06t13: Allow to omit skill name when only one skill is
modified
  - s06t15: Rework `_status.py` internals to typed structures
  - s06t16: Auto-attach untracked skills on `update` when they
match source exactly (tb) <<<
    - s06t1601: Attach a uniquely-matching untracked skill
    - s06t1602: Attach ambiguity handling & filter integration
  - s06t18: Update specific source (tc) <<<
    - s06t1801: Extract target-skill collection as a seam
    - s06t1802: `-s/--source` filters the update work set
    - s06t1803: Derive pulls from the collected skill set
  - s06t19: Allow to edit `source` skills directory (td) <<<
    - s06t1901: Extract shared idempotent init/config
implementation
    - s06t1902: `--skills-dir` option with strict validation
    - s06t1903: `skills init` + `skills source config` command
surface
  - s06t20: Multiple source support
  - s06t21: Ignore uncommitted changes when they do not relate to
skills
  - s06t22: Support project-level skills

# greendwin @ ecimbalyuk in ~/repo-skills on git:main o [0:32:04]
$ tasker list --todo
s02: Rework repo workflow (ta)
  - s02t13: Release v1.0
s06: Usability (q)
  - s06t16: Auto-attach untracked skills on `update` when they
match source exactly (tb)
    - s06t1601: Attach a uniquely-matching untracked skill
    - s06t1602: Attach ambiguity handling & filter integration
  - s06t18: Update specific source (tc)
  - s06t19: Allow to edit `source` skills directory (td)
```
