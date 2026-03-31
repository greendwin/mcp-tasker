---
id: s18t07
status: done
---

# Give access to tasks as a resource

Resource desk

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

## Subtasks

- [x] [s18t0701](s18t0701-resource-index.md): Add resource 'task://index' to list all root tasks
- [x] s18t0702: Register root resources 'task://{ref}' for root tasks
- [x] s18t0703: Register nested resources when viewing parents
- [x] [s18t0704](s18t0704-nested-tasks.md): Show list of nested resources on viewing current resource
