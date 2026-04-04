---
id: s09t13
slug: show-deleted-tasks-on-preview
status: done
---

# Show deleted tasks on preview

* We need special marks to show deleted tasks.
* Lets not detach deleted tasks from parents.
* Lets rework flushing back from tasks iterator to hierarchical walk as were before -- so no need to build full path from root on each task.
* On render we should skip deleted subtasks.
* No need to write list of deleted tasks in case of preview
