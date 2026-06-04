---
id: s13t0704
slug: remove-resources-retire-models-docs
status: pending
---

# Remove resources, retire models, docs and tox

**Goal:** delete the redundant MCP resource surface and finish the cleanup so the whole task lands green.

**Decisions & constraints:**
- Remove `resource_task` / `resource_task_index` and their `@mcp.resource` registrations entirely. No external consumer, agents work through tools, and a second (now redundant) surface isn't worth maintaining -- "deprecate with no consumers" = delete. Keep-and-convert-to-markdown rejected.
- Drop the removed symbols from `src/tasker/mcp/__init__.py` (`__all__` and imports).
- Delete `TaskInfo` / `TaskPreview` from `_model.py` -- now unused after Slices 1-3 (reads went text/markdown, mutators use the new result model). `_model.py` may end up empty/removed.
- Update `DESIGN.md`: remove the Resources table; refresh the Tools table to describe the new text/markdown returns and document the single-char status legend.
- Migrate `tests/test_mcp_status.py` read-backs from `resource_task(...)` to the repo / `Task` model -- a test must not verify one MCP method via another.
- Delete `tests/test_mcp_resources.py`.

**Edge cases:**
- No lingering imports of removed symbols anywhere (`grep` for `resource_task`, `TaskInfo`, `TaskPreview`, `task://`).
- `__all__` stays accurate; `import tasker.mcp` succeeds.

**Key files:** `src/tasker/mcp/_view_methods.py`, `src/tasker/mcp/_model.py` (emptied/deleted), `src/tasker/mcp/__init__.py`, `DESIGN.md`, `tests/test_mcp_resources.py` (delete), `tests/test_mcp_status.py`.

**Acceptance criteria:**
- The `task://` resources and `resource_*` functions no longer exist; `import tasker.mcp` succeeds with an updated `__all__`.
- `DESIGN.md` has no Resources table and its Tools table reflects the new outputs + status legend.
- `uv run tox` is green across all environments, with all issues fixed (including any pre-existing).
