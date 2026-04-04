---
id: s11t15
slug: support-loading-archived-tasks-in
status: pending
---

# Support loading archived tasks in TaskRepo

* Refactor existing code, all moves/deletes must be peroformed automagically in `flush_to_disk`
* Add `archived` flag to `Task` object, so that it changes its file location
* Rework existing code, where `TaskRepo` is initialized on `tasker/archived` directory
