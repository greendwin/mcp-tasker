---
id: s19t36
slug: accept-multiple-task-ids-in
status: pending
---

# Accept multiple task ids in MCP mutator tools

## Context

The MCP mutators are singular — `start_task`, `review_task`, `finish_task`, `cancel_task`, `reset_task` and `edit_task` all take one `task_ref: str` — while their CLI twins are variadic. Only `view_tasks` and `order_tasks` take lists. So an agent closing out six subtasks issues six round trips.

Split out of [s19t35] (range expressions), which deliberately left MCP alone: range expressions are a **human input affordance** and are not the answer here. Agents should pass explicit ids; what they need is a list parameter, not a shorthand grammar.

## Decisions

- Widen the mutators to accept several **explicit ids** per call, mirroring the CLI's variadic arguments. Range expressions remain undocumented for MCP (they resolve if passed, but are not advertised — see [s19t35]).

## Open questions

- Parameter shape: `task_refs: list[str]` matching `view_tasks`/`order_tasks`, versus keeping `task_ref` and accepting `str | list[str]`.
- Return shape: `MutationResult` today. Does a multi-task call return a list, or a single result summarising all of them? This is the main design question and the reason it was not folded into [s19t35].
- Whether partial failure (three of six invalid) fails the whole call or reports per-task outcomes, the way `view_tasks` degrades a bad ref into an error stub rather than failing the batch.
- Whether these should adopt the action-report outcome vocabulary from ADR 0004, which is currently CLI-only (the reporter is print-only and silent under `--json-output`).

## Out of scope

- `.recent` handling is unchanged: ADR 0004 contract 1 forbids MCP mutators from touching it, regardless of how many tasks a call affects.
- CLI behaviour — already variadic.
