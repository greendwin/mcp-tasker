---
id: s25t02
slug: support-manager-dashboard
status: pending
---

# Support manager dashboard

We need 'todo' dashboard to peak tasks that we're planning to implement.

## Implementation

* Add `TODO` section (it's a file `TODO.md` in `tasker` dir).
* Add command `tasker todo TICKET` and `tasker backlog TICKET`.
* Support `list --todo` and corresponding MCP method.
* Highlight tickets in TODO on `list` command.

## Open questions

* How to cleanup TODO list? This cannot be automatically, since finished tasks in review could be reviewed.
* We can clean it when archiving a task.
* We still need `untodo` comman.
