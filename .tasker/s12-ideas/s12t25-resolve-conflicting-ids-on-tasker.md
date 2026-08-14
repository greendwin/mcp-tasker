---
id: s12t25
slug: resolve-conflicting-ids-on-tasker
status: cancelled
---

# Resolve conflicting ids on 'tasker resolve'

It would be nice if we can resolve conflicts when there are two tasks were created with the same id in different branches. We can keep our branch' id and their rename to next free id.

This task is out of single-file resolution, since it should not only check other files, that potentionally have no conflicts (due to diffrent slug value), but also recursive renaming of all nested subtasks for moving task.

TBD: can we reconstruct their TaskRepo, perform rename and reapply to current merge?
Problem is that there can be other pending merge conflicts that still should be resolved.
