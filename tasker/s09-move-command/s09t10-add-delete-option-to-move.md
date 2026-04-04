---
id: s09t10
slug: add-delete-option-to-move
status: pending
---

# Add `--delete` option to 'move' command

* add `deleted` flag to `Task` object
* all deletions must be performed on `flush_to_disk` (source deleted, new task not saved)
