---
id: s13t09
slug: make-frontmatter-forward-compatible
status: in-progress
---

# Make frontmatter forward-compatible

## Context

The front-matter parser rejects unknown keys ("Unknown front-matter field"), so an
older tasker crashes on files written by a newer version (this happened when
`order` was introduced) and other tools cannot annotate tasks without breaking
them. Make front matter forward-compatible: unknown keys survive tasker's edits
and merge cleanly. Decisions recorded in ADR 0005 and CONTEXT.md
("Frontmatter extras").

## Decisions

- **Full YAML parsing via PyYAML** (`safe_load`/`safe_dump`, new runtime
  dependency) — preservation is data-level: nested structures and types
  round-trip; comments and exact formatting do not (documented). *Rejected:
  verbatim raw-line preservation (byte-stable but unmergeable per key, no
  data-level guarantee); ruamel.yaml round-trip mode (comment fidelity is
  marginal for machine-managed files; `CommentedMap` would leak into the model).*
- **Owned keys stay template-rendered** — `id`, `slug`, `status`, `order` keep
  their current validation and fixed rendering order; all other keys land in a
  new `extra: dict` field on `Task`, re-emitted after the owned keys in
  first-seen order (`safe_dump(sort_keys=False)`). A key positioned above
  `status:` normalizes below it on first rewrite, then stays stable — same
  philosophy as `## Subtasks` always moving last. *Rejected: emitting the whole
  mapping as one YAML dump (preserves positions but risks cosmetic churn on
  every existing file and moves owned-field rendering out of the template).*
- **Merge per top-level key** — extras merge with the existing `_merge_field`
  three-way logic, key by key (deep value equality); a key changed differently
  on both sides emits a conflict block with each side's YAML dump. *Rejected:
  whole-blob merge (two tools touching different keys must merge cleanly — that
  is the core use case).*
- **Extras block downgrade to inline** — guard added next to the `description`
  check in `update_task_status_and_flags`; an inline bullet has no front
  matter, and silently deleting another tool's annotations breaks the contract.
  Extends ADR 0003's "no other reason to be a file" rule.
- **No reserved names** — internal-looking keys (`title:`, `extended:`,
  `subtasks:`) are preserved silently like any other extra; a future tasker that
  claims a key migrates its value out of `extra` itself. *Rejected: erroring on
  tasker model-field names (recreates the exact forward-compat failure this task
  removes).*
- **Remaining validation** — invalid YAML or a non-mapping block, and bad
  owned-key values (unknown `status`, non-int `order`) still raise
  `TaskValidateError`; the "Unknown front-matter field" error is removed.

## Open questions

- none

## Out of scope

- Subtask bullet grammar or body annotations — front matter only.
- Comment/formatting preservation (explicitly traded away with PyYAML).

## Subtasks

- [~] [s13t0901](s13t0901-switch-frontmatter-parsing-to-yaml.md): Switch frontmatter parsing to YAML
- [ ] [s13t0902](s13t0902-preserve-unknown-frontmatter-keys-via.md): Preserve unknown frontmatter keys via extra on Task
- [ ] [s13t0903](s13t0903-per-key-three-way-merge.md): Per-key three-way merge of frontmatter extras
- [ ] [s13t0904](s13t0904-extras-keep-a-task-file.md): Extras keep a task file-based (block downgrade to inline)
