---
id: s13t0701
slug: render-core-listtasks-as-concise
status: pending
---

# Render core + list_tasks as concise text

**Goal:** `list_tasks` returns a compact text block (including `todo=True`), establishing the shared rendering vocabulary used by later slices.

**Decisions & constraints:**
- Compact text lines, one per task: `<sign> <id>  <truncated-title...> (...)`. Drops the repeated JSON keys that dominate a structured array.
- Single-char status signs (legend in the `list_tasks` docstring, sent once): `.` pending, `~` in-progress, `?` in-review, `x` done, `-` cancelled. Distinct per status -- the CLI's `_CHECKBOX` is deliberately lossy (merges in-review/in-progress and done/cancelled) and must NOT be reused; an agent needs the in-review vs in-progress distinction. `~`/`x` intentionally match the CLI vocabulary.
- Title truncation ~60 chars on a word boundary, ellipsis only when actually cut. Word-boundary (not hard cut) avoids mid-word noise; 60 (not 40) keeps enough to disambiguate long shared prefixes like "BUG: when searching for...".
- `(...)` has-body marker: trailing suffix when `description`/`extra_sections` is non-empty -- signals "title isn't the whole story, view it". Distinct from the truncation ellipsis (which attaches to the title). NOT driven by subtask presence.
- Empty-state sentinels: `No tasks` for an empty root list; `All tasks finished!` for the all-closed todo case (mirrors `src/tasker/cli/_view_commands.py`). Empty string is rejected -- ambiguous between "empty" and "failure".
- New private `src/tasker/mcp/_render.py` holding pure, independently unit-testable functions: `status_sign`, `truncate_title`, `render_task_line`, `render_task_block`. The render layer is the deep module the whole task is built around.
- All-finished detection mirrors the CLI todo logic: `load_todo_tasks` returns live tasks; when the todo list is non-empty but every task is closed, emit the finished message.

**Edge cases:**
- Empty root list.
- Empty todo list vs all-finished todo list.
- Task with a body but a short (un-truncated) title: marker, no ellipsis.
- Long title, no body: ellipsis, no marker.
- Varying id widths (root `s26` vs subtask `s26t15t01`).

**Key files:** `src/tasker/mcp/_render.py` (new), `src/tasker/mcp/_view_methods.py`, `tests/test_mcp_view.py`, possibly a small helper in `src/tasker/todo.py`.

**Acceptance criteria:**
- `list_tasks()` returns lines like `~ s26t14  Description can be null in MCP... (...)`.
- Each status renders its distinct sign; in-review (`?`) differs from in-progress (`~`).
- A title over 60 chars is cut on a word boundary with a trailing ellipsis; a title at/under 60 is untouched.
- A task with a body gets the ` (...)` suffix; one without does not.
- Empty root list returns `No tasks`; a todo list with all tasks closed returns `All tasks finished!`.
