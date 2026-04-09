---
id: s25t02
slug: support-manager-dashboard
status: pending
---

# Support manager dashboard

Add a personal TODO dashboard to flag tasks for upcoming work.

## Storage

- `.todo` file in `tasker/` dir, next to `.recent`
- Plain list of task IDs, one per line
- Git-ignored; `.gitignore` updated lazily on first `tasker todo` write

## CLI Commands

- `tasker todo <task-id>...` — add tasks to `.todo`, resolves refs, idempotent, prints confirmation
- `tasker untodo <task-id>...` — remove tasks from `.todo`, idempotent, prints confirmation
- `tasker list --todo` — filter mode, shows only `.todo` tasks, sorted by task ID
- `tasker list` — shows `(todo)` marker on tasks in `.todo`

## Cleanup

- Auto-remove from `.todo` on `archive`
- Otherwise manual via `untodo`

## MCP

- `list_tasks` gets a `todo` boolean param for filtering
- No `todo_task`/`untodo_task` tools — human-only curation

## Behavior

- Refs are resolved (validates existence, supports `q`/`p` shortcuts)
- Multiple IDs accepted
- Idempotent (silent on duplicates/missing)

## Implementation

* Add `TODO` section (it's a file `TODO.md` in `tasker` dir).
* Add command `tasker todo TICKET` and `tasker backlog TICKET`.
* Support `list --todo` and corresponding MCP method.
* Highlight tickets in TODO on `list` command.

## Open questions

* How to cleanup TODO list? This cannot be automatically, since finished tasks in review could be reviewed.
* We can clean it when archiving a task.
* We still need `untodo` comman.

## Subtasks

- [x] s25t0201: Add .todo file support (read/write/gitignore)
- [x] s25t0202: Add `todo` and `untodo` CLI commands
- [x] [s25t0203](s25t0203-show-todo-marker-in-list.md): Show (todo) marker in `list` output
- [x] [s25t0204](s25t0204-add-list-todo-filter-mode.md): Add `list --todo` filter mode
- [x] s25t0205: Auto-remove from .todo on archive
- [ ] s25t0206: Add `todo` param to MCP `list_tasks`
- [ ] s25t0207: TBD: split _task_commands
- [ ] s25t0208: TBD: should we move print, resolve and etc. packages to core subpackage
- [x] ~~s25t0209: Todo-marked tasks must be shown in default list view same as recently closed~~
- [ ] s25t0210: Support cancel_task in MCP
