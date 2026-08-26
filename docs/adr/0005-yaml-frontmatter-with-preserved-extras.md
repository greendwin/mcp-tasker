---
status: accepted
---

# Front matter is parsed as YAML; unknown keys are preserved as data, not text

The front-matter parser used to match only the owned keys (`id`, `slug`,
`status`, `order`) line-by-line and reject anything else — so an older tasker
crashed on files written by a newer version (this happened when `order` was
introduced), and no other tool could annotate a task without breaking it. We now
parse the whole block with YAML (PyYAML `safe_load`), keep the owned keys'
existing validation, and carry every other key as [Frontmatter extras] — a
structured `extra` mapping on the task model.

Preservation is **data-level, not byte-level**: extras survive as parsed YAML
values and are re-emitted (`safe_dump`, insertion order) after the owned keys,
so nesting and types round-trip but comments and exact formatting do not, and a
key written above `status:` is normalized below it on first rewrite. This
mirrors how the body already normalizes (`## Subtasks` always moves last).

- No names are reserved: keys that look internal (`title:`, `extended:`) are
  preserved silently like any other extra. A future tasker that claims a key
  migrates its value out of `extra` itself; erroring on "suspicious" keys would
  recreate the exact forward-compatibility failure this ADR removes.
- Merge (`resolve`) treats extras per top-level key with the same three-way
  scalar merge as owned fields: different keys changed on different branches
  merge cleanly; the same key changed both ways emits a conflict block with each
  side's YAML dump.
- A task carrying extras cannot be downgraded to an inline subtask bullet
  (extras join `description` in the downgrade guard) — an inline bullet has no
  front matter, and silently deleting another tool's annotations would break the
  contract this ADR exists to provide. This extends ADR 0003's "no other reason
  to be a file" rule: extras are such a reason.

## Considered Options

- **Preserve unknown lines verbatim** (opaque list of raw strings, byte-stable
  round-trip, no new dependency). Rejected: text blobs cannot be merged per key,
  and downstream tools get no guarantee their values survive as *data* — a
  reflowed or reordered writer would still conflict textually.
- **ruamel.yaml round-trip mode** to also preserve comments and formatting.
  Rejected: comment fidelity in machine-managed task files is marginal, and
  ruamel's round-trip objects (`CommentedMap`) would leak into the task model or
  need careful containment; PyYAML keeps the model plain data.
