---
id: s12t12
slug: shared-tasker-aka-20
status: pending
---

# Shared Tasker (aka 2.0)

We need to store tasker out of repo, but still to sync it.
Idea is to init it elsewhere as a saparate git repo and link it from project - which repo and **subproject**.

So far user can have *multiple* projects in the same repo (TBD: we need to be able to see cross-project tasks lists and edit them).

Tasker should manage its repo by itself (commit/merge/push/pull).
We need a soft way to resolve conflicts if any -- let LLM to resolve it using mcp.

Referenced repos could be stored in `~/.local/share/tasker/repos`.
Also we need migration from old-style (should still support it) to shared repo.
