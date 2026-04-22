---
id: s12t08
slug: show-recently-finished-task-in
status: done
---

# Show recently finished task in list command, otherwise it is vanishing from radars as soon as it marks done

Show recently closed tasks in `list` command so they don't vanish from radar immediately.

## Design

1. **"Recently closed"** = all tasks closed in the last `done` or `cancel` invocation
2. **Storage**: Extend `.recent` file to JSON format: `{"recent": "s01t02", "closed": ["s01", "s01t01"]}`
3. **Backward compatibility**: Check for opening `{` bracket to detect JSON vs legacy plain-text format
4. **Display**: Show recently-closed tasks inline in their normal tree position (not filtered out), using existing green `[x]` styling — no extra marker
5. **Parent visibility**: Force parent chain to appear if a recently-closed subtask needs to be shown
6. **Force-close**: Track all recursively closed tasks, not just the explicit target
7. **No cleanup on reset/start**: Don't remove tasks from `closed` on other operations
8. **CLI-only**: MCP methods are not affected
