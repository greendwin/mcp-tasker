# Unified task body (single field, no description/extra-sections split)

A task's free-form content is stored as a single `description` field holding the
whole body. We previously split it into `description` (text before the first `##`)
and `extra_sections` (the other non-Subtasks `##` sections), but only the read
side (`view_tasks`) merged them while writes (`edit_task`, CLI `edit -d`) set just
`description` — leaving the orphaned `extra_sections` on disk and duplicating the
body on every edit. Collapsing to one field makes the write contract match the read
contract and removes per-field bookkeeping across parse/render/merge/print/loader.
The `## Subtasks` section stays managed and parsed out separately.

## Consequences

- 3-way merge (`merge.py`) now treats the body as one unit: a branch editing only
  the lead paragraph and another editing only a section, which used to auto-merge,
  now conflict. This granularity loss was judged marginal (the merge was already
  whole-string per field) and worth the correctness and simplicity gain.

## Considered Options

- **Unmerge-on-write** — keep both fields and re-split the incoming body on every
  write. Rejected: preserves the marginal merge granularity but keeps the
  conceptual seam and the standing risk that future code reintroduces the
  read/write asymmetry.
