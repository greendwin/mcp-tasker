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

**Task id**:
The canonical, unique identity of a task — `s19` for a root task, `s19t3502` for a
nested one. The only currency below the resolution boundary: every function that
is not parsing user input speaks task ids.
_Avoid_: ref, task ref

**Task ref**:
Whatever a user types to point at tasks — a task id, a recent shortcut (`q`, `p03`,
`ta`), a root-task name (`bugs`), or a batch expression. A ref may denote more than
one task, so resolving one yields a list of [Task id]s. Exists only at the CLI and
MCP boundary.
_Avoid_: task id, selector, reference string

**Range expression**:
A [Task ref] that names a span of siblings under one anchor, written as a
comma-separated list of ranges over that anchor's children — `s19t10-15,17`, where
a lone group like `17` is a one-element range. Always confined to a single sibling
set: an expression cannot cross parents.
_Avoid_: batch selection, batch expression, glob

**Filename stem**:
The on-disk name of a task's file or directory, `<task id>-<slug>`. Purely a
filesystem concern — it is never accepted as user input and never the identity of a
task.
_Avoid_: ref, task ref, full ref

**Frontmatter extras**:
Frontmatter keys that `tasker` does not own (the owned keys are `id`, `slug`,
`status`, `order`). Held as data, not text: preserved across edits and merged
per-key on three-way merge; comments around them are not preserved. A task
carrying extras cannot become an inline subtask. Purpose: let newer `tasker`
versions and other tools annotate tasks without older versions rejecting or
destroying the annotations.
_Avoid_: unknown fields, custom fields, extra annotations

**Order**:
A per-sibling-set manual sort key expressing implementation order. Among siblings,
tasks with an order sort ahead of those without, ascending; ties and unordered
tasks fall back to [id] order. Purpose: pull the next tasks to the front to match
the intended sequence of work, without renaming ids. Only meaningful relative to
siblings under the same parent.
_Avoid_: priority, rank, position
