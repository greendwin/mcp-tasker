---
id: s18
slug: mcp-server
status: done
---

# Create MCP server to let agent use tasker directly

## Subtasks

- [x] s18t01: Create 'hello world' stdio MCP server
- [x] s18t03: Support 'mcp' command
- [x] s18t04: Support 'mcp --port NN' to start mcp server as a host
- [x] ~~s18t05: Add instructions on how to configure MCP server~~
- [x] s18t06: Support view commands: `list` and `view`
- [x] s18t08: Support status commands: `start`, `reset`, `done`
- [x] [s18t07](s18t07-task-as-resource/): Give access to tasks as a resource
- [x] s18t09: Don't load full tree in 'list' and 'index' methods - parse root resources without loading full tree
- [x] s18t10: Add 'force' flag to 'finish_task'
- [x] [s18t11](s18t11-support-task-creation.md): Support task creation
- [x] s18t12: Dont show titles in view_task's subtasks -- let AI invoke subsequent view to show task details, not only summary
- [x] s18t13: Add view_tasks command or exstend existing, allow to pass mulitple task IDs
- [x] s18t14: Group tasks by status in task info
- [x] s18t15: Add 'edit_task' method to let agent update task description, title and slug
