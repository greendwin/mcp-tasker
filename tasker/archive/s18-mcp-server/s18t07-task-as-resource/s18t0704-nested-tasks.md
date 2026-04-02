---
id: s18t0704
slug: nested-tasks
status: done
---

# Show list of nested resources on viewing current resource

Return rosource in following format:

```json
{
    "ref": "s01t0203-slug",
    "title": "Task title",
    "description": "Task description" | null,
    "status": "pending",
    "subtasks": [
        {"ref": "s01t020301", "title": "subtask - 01"},
        {"ref": "s01t020302", "title": "subtask - 02"},
        {"ref": "s01t020303", "title": "subtask - 03"},
    ]
}
```
