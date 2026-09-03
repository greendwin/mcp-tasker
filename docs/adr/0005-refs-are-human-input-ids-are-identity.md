---
status: proposed
---

# Refs are human input, ids are the only identity, slugs belong to filenames

`tasker` used one word — *ref* — for three different things: the canonical
identity of a task (`s19t35`), the on-disk filename stem (`s19t35-support-batch-
selection`), and whatever a user typed to point at a task (`q`, `p03`, `ta2`,
`bugs`). Because the filename-stem form was also accepted as input and silently
stripped by `parse_task_ref`, some functions required a bare id and others
tolerated a slug tail, with no way to tell which from a signature. We split the
three apart: a [Task ref] is user input at the CLI/MCP boundary only, a [Task id]
is the sole currency below that boundary, and a [Filename stem] is a filesystem
concern that is never accepted as input.

The occasion was batch selection — letting a user write `s19t10-15,17` to name a
span of siblings. `-` is the natural separator and the one users reach for, but
it was already the slug delimiter, so the two forms collided on any ref whose
slug is entirely numeric. We could have disambiguated by shape and kept both;
instead we dropped slug refs on input, because the collision was a symptom of the
conflation rather than the disease.

Concretely: `Task.ref` becomes `Task.filename_stem`; every `task_ref` parameter
below `resolve_ref` is renamed `task_id`, so a surviving `task_ref` deep in the
call graph is a grep-able defect; `--json-output` emits `task_id`/`task_ids`
instead of `task_ref`/`task_refs`, and their values are ids; user-facing result
lines print ids, which is what ADR 0004 already required of authoritative result
reporting. Resolution becomes one-to-many — a single ref may name several tasks —
so single-ref call sites (`view`, `edit`, `add <parent>`, `move --attach`, and
the MCP mutators) enforce arity explicitly rather than assuming it.

## Consequences

- **Breaking.** `tasker view s19t35-my-slug` stops working, including refs
  produced by tab-completion and by copy-pasting a filename or a
  `[s19t35](s19t35-my-slug.md)` link target. We reject it with a targeted message
  naming the id to use instead, rather than a generic parse error, and ship it as
  an explicit breaking change rather than behind a deprecation warning — a
  compatibility shim would keep alive precisely the dual-mode parser this
  decision exists to delete.
- Shell completion now offers bare ids; the task title, already the completion
  description, carries the human-readable context the slug used to.
- Batch expressions are a human affordance. They are not advertised in MCP tool
  schemas, though they are not blocked either: an agent should pass a user's
  shorthand through verbatim rather than resolve it itself. Recent-shortcuts
  (`q`, `p`, `t<letter>`) additionally must never be *constructed* by an agent,
  since they resolve against `.recent`, which per ADR 0004 MCP calls do not
  update.

## Considered Options

- **Keep slug refs and disambiguate by shape** — treat a trailing `-<digits>` as
  a range endpoint and anything else as a slug. Costs nothing at the boundary and
  breaks no existing input. Rejected: it leaves the ref/id ambiguity in every
  signature below the boundary, which is the larger and longer-lived problem; the
  grammar collision was the prompt, not the point.
- **Use `..` as the only range separator**, sidestepping the collision entirely
  and leaving slug refs untouched. Rejected for the same reason, and because it
  makes the common closed range (`s19t10-15`) the awkward spelling. `..` is still
  accepted, and is the *only* spelling permitted for open-ended ranges.
- **Deprecate with a warning for one minor release.** Rejected: the warning path
  requires retaining the slug-stripping code for a release, deferring the
  refactoring that motivates the change.
