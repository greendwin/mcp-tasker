# tasker

Glossary for `tasker`, a file-based task tracker for git repositories. Defines the
terms used when talking about a task's stored content.

## Language

**Task body**:
All free-form prose of a task — the lead paragraph plus any `##` sections the
user writes (Context, Decisions, Notes, …) — held as a single field. It excludes
the managed `## Subtasks` section. The MCP `description` argument and the CLI
`--details` option both set the whole body; there is no separate "lead paragraph"
vs "extra sections" concept exposed or stored.
_Avoid_: description (lead-only sense), extra sections, details

**Managed section**:
A `##` section whose content `tasker` owns and renders from structured data rather
than preserving verbatim. `## Subtasks` is the only managed section; it is always
normalised to the end of the file. Every other `##` section is part of the
[Task body] and preserved as written.
_Avoid_: reserved section, special section

**Order**:
A per-sibling-set manual sort key expressing implementation order. Among siblings,
tasks with an order sort ahead of those without, ascending; ties and unordered
tasks fall back to [id] order. Purpose: pull the next tasks to the front to match
the intended sequence of work, without renaming ids. Only meaningful relative to
siblings under the same parent.
_Avoid_: priority, rank, position
