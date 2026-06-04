---
id: s26t15
slug: concise-mcp-outputs
status: pending
---

# Review outputs in MCP methods -- should be concise

## Context

MCP method outputs are verbose: mutators echo back caller-supplied text (titles, descriptions the agent just wrote), and reads return JSON whose repeated field keys and escaped-markdown bodies waste agent context. The goal is concise outputs -- no echo of what the caller already has, minimal scannable data for lists, and full detail only when explicitly viewed -- so agents spend fewer tokens per task operation.

## Decisions

- **No echo on mutators** -- `start/review/reset/cancel/finish_task`, `create_task`, `edit_task` return structured `{id, status}` (full enum status). The resolved `id` is genuinely new info when the caller passed a shortcut/slug; everything else (title, description) is echo. *Rejected: returning full `TaskInfo` (pure echo); a bare status or confirmation string (loses the resolved id, less machine-clean than tiny JSON).*
- **Force cascades report affected ids** -- `reset/cancel/finish_task` add `affected: [ids]` only when `force` actually cascaded to subtasks, surfacing the side effect without echoing child objects. *Rejected: hiding the cascade; always returning full subtask objects.*
- **`list_tasks` -> compact text block**, one line per task: `<sign> <id>  <truncated-title...> (...)`. Drops repeated JSON keys that dominate a structured array. *Rejected: structured trimmed objects (still pay per-row keys).*
- **Single-char status signs** (legend in docstring, sent once): `.` pending, `~` in-progress, `?` in-review, `x` done, `-` cancelled. Distinct per status (the CLI's lossy `_CHECKBOX` merges in-review/in-progress and done/cancelled, which an agent can't tolerate). `~`/`x` match the CLI. *Rejected: reusing `_CHECKBOX`; letter signs.*
- **Title truncation** ~60 chars on a word boundary, ellipsis only when cut -- uniform scan width, enough to disambiguate long shared prefixes ("BUG: when searching for..."). *Rejected: word-count budget (unpredictable width); 40-char (too tight); hard mid-word cut.*
- **`(...)` has-body marker** -- trailing suffix on a `list_tasks`/subtask line when the task has `description`/`extra_sections`, signalling "title isn't the whole story, view it". Distinct from the truncation ellipsis (attached to title). Not driven by subtask presence. *Rejected: `+` after id; `(+details)` (preferred shorter).*
- **`view_tasks` -> trimmed markdown** -- `# <id>: <full title>`, `status:`/`parent:` metadata lines (parent omitted for roots), body sections verbatim, `## Subtasks` reusing the `list_tasks` line format. Body is already markdown, so JSON-wrapping just escapes newlines and pays key overhead. *Rejected: keeping structured `TaskInfo`; reusing `task.md.j2` verbatim (its frontmatter + file links are disk artifacts, noise/misleading over MCP).*
- **Multiple views separated by `---`** -- unambiguous section break even when task bodies contain their own `#`/`##` headings. *Rejected: blank-line gap only.*
- **Graceful bad ref in `view_tasks`** -- a bad/deleted ref renders a per-ref error stub (`# <ref>: <error>`, including the `TaskValidateError` message) and the batch continues. Consistent with the project's s26t02/s26t08 stance. *Rejected: failing the whole batch on one stale id.*
- **Empty-state sentinels** -- `No tasks` for an empty root list; `All tasks finished!` for the all-finished todo case (matches the CLI). *Rejected: empty string (ambiguous: empty vs failure).*
- **Resources removed** -- delete `resource_task`/`resource_task_index` and their `@mcp.resource` registrations; drop from `__init__.py` and the DESIGN.md table. No external consumer, agents work through tools, and they'd be a redundant second surface. `TaskInfo`/`TaskPreview` retire in favor of the small mutation-result model + render functions. *Rejected: keep-and-convert-to-markdown.*

## Open questions

- Mutation-result model shape -- one model with optional `affected` vs a base `{id, status}` + extended `{id, status, affected}`. Deferred to implementation.
- Render-function module placement -- likely a private `mcp/_render.py`. Deferred to implementation.

## Out of scope

- Changing `list_tasks`/`view_tasks` parameters or filtering semantics (e.g. `todo` behavior, what `load_todo_tasks` returns) -- only the output format changes.
- CLI output (`render.py`, templates) -- untouched; the lossy `_CHECKBOX` stays as-is for the CLI.
- Adding new MCP tools or new fields beyond `affected`.

## Subtasks

- [ ] [s26t1501](s26t1501-render-core-listtasks-as-concise.md): Render core + list_tasks as concise text
- [ ] [s26t1502](s26t1502-viewtasks-as-trimmed-markdown.md): View_tasks as trimmed markdown
- [ ] [s26t1503](s26t1503-mutators-return-id-status-plus.md): Mutators return {id, status} plus affected on force
- [ ] [s26t1504](s26t1504-remove-resources-retire-models-docs.md): Remove resources, retire models, docs and tox
