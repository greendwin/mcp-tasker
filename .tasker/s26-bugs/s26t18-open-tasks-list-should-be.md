---
id: s26t18
slug: open-tasks-list-should-be
status: pending
---

# Open tasks list should be grouped

When trying to call `tasker done --rev`, it shows a list of opened task
as a plain list; it should be grouped (see same in --todo list)

```
# greendwin @ LAPTOP-C4SLVRPI in ~/mcp-tasker on git:gitbutler/workspace x [23:58:25]
$ t done --rev
No tasks to close.

Open tasks:
  - s12t12: Shared Tasker (aka 2.0)
  - s12t14: When moving tasks -- update all references ID to moved tasks
  - s12t15: Add 'depends-on' links to tasks
  - s12t18: Support -p suffix, like 'tap' aka parent of 'ta'
  - s12t20: Get rid of sXXtYY ids
  - s12t21: Support merging archived tasks in 'tasker resolve'
  - s12t22: Install shortcuts to .bashrc of .zshrc/.zshuser
  - s12t23: Todo list must be commited to git, don't ignore it
  - s12t24: Order tasks in 'list' by 'depends-on' relations
  - s12t25: Resolve conflicting ids on 'tasker resolve'
  - s12t26: Tasker UI
  - s13t06: Rework error messages
  - s19t22: 'tasker add XXX' should open editor with placeholders, same for 'tasker new'
  - s19t32: Interactive mode for 'tasker list'
  - s19t33: Add mpc installation helper 'tasker mcp --install'
  - s19t34: Get rid of 'subtasks' section
  - s28t02: [~] Display sort by (order, id)
  - s28t03: Clear order on plain move
  - s28t04: Sparse reorder engine (deep module)
  - s28t05: CLI: tasker order &lt;anchor&gt; &lt;moved...&gt; (base)
  - s28t06: CLI: tasker order --clear
  - s28t07: CLI: tasker order --front
  - s28t08: CLI: tasker order --front --rest
  - s28t09: CLI: tasker order --parent (attach + order)
  - s28t10: MCP: order_tasks(task_refs)
  - s28t11: Resolve / merge wiring for order
```
