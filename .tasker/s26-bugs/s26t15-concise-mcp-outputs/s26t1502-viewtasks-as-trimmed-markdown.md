---
id: s26t1502
slug: viewtasks-as-trimmed-markdown
status: pending
---

# View_tasks as trimmed markdown

**Goal:** `view_tasks` returns trimmed markdown instead of a structured `TaskInfo`.

**Decisions & constraints:**
- Single-task layout: `# <id>: <full title>` (full, un-truncated title -- this IS the detail view), then `status:` / `parent:` metadata lines (`parent:` omitted for root tasks), then body sections (`description` + `extra_sections`) verbatim, then `## Subtasks` reusing the Slice 1 line format (`render_task_line`).
- Multiple tasks joined by `\n\n---\n\n` -- an unambiguous markdown section break even when a task body contains its own `#`/`##` headings. Blank-line-only separation rejected.
- Bad/deleted ref -> per-ref error stub `# <ref>: <error message>` (include the `TaskValidateError` message so the agent learns why: deleted vs unknown vs malformed) and continue the batch. Failing the whole batch on one stale id is rejected -- consistent with the project's s26t02/s26t08 stance.
- Do NOT reuse `task.md.j2` verbatim: its YAML frontmatter and `.md`/dir file links are disk-file artifacts that are noise or misleading over MCP.
- Body is already markdown, so wrapping it in JSON just escapes newlines and pays key overhead -- markdown is the natural representation.
- Add `render_task_markdown(task)` and a per-ref error renderer to `_render.py`. `view_tasks` no longer constructs `TaskInfo`. Children reuse `render_task_line`.

**Edge cases:**
- Root task (no `parent:` line).
- Task with only `extra_sections` and a null `description`.
- Task with no subtasks (no `## Subtasks` section).
- A batch mixing good and bad refs.
- A child whose own body contains `#`/`##` headings (the `---` separator must still delimit cleanly).

**Key files:** `src/tasker/mcp/_render.py`, `src/tasker/mcp/_view_methods.py`, `tests/test_mcp_view.py`.

**Acceptance criteria:**
- `view_tasks(["s26"])` returns markdown with the heading, a `status:` line, the body, and a `## Subtasks` checklist using the single-char signs.
- A root task omits `parent:`; a subtask includes it.
- `view_tasks(["s26", "s99t99"])` returns the good task plus a `# s99t99: <error>` stub, separated by `---`, without raising.
