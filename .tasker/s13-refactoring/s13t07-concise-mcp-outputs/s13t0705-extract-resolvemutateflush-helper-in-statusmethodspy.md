---
id: s13t0705
slug: extract-resolvemutateflush-helper-in-statusmethodspy
status: done
---

# Extract resolve-mutate-flush helper in _status_methods.py

The resolve-mutate-flush triplet (`get_repo()`, `resolve_ref(repo, task_ref).task`, `repo.<verb>(...); repo.flush_to_disk()`) is repeated 6 times across all status-change MCP tools in `src/tasker/mcp/_status_methods.py`. Two tools (`cancel_task`, `finish_task`) add a `save_closed_refs` step.

Extract a small helper that handles the common pattern. The two tools needing `save_closed_refs` can call it and do the extra step, or the helper can accept an optional post-action callback.

Source: duplication lens finding from s13t0701 dev-loop.
