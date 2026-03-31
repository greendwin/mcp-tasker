---
id: s18
status: pending
---

# Create MCP server to let agent use tasker directly

## Subtasks

- [x] s18t01: Create 'hello world' stdio MCP server
- [x] s18t03: Support 'mcp' command
- [ ] s18t04: Support 'mcp --port NN' to start mcp server as a host
- [x] ~~s18t05: Add instructions on how to configure MCP server~~
- [x] s18t06: Support view commands: `list` and `view`
- [x] s18t08: Support status commands: `start`, `reset`, `done`
- [x] [s18t07](s18t07-task-as-resource/): Give access to tasks as a resource
- [ ] s18t09: Don't load full tree in 'list' and 'index' methods - parse root resources without loading full tree
- [x] s18t10: Add 'force' flag to 'finish_task'
