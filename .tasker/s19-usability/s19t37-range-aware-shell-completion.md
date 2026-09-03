---
id: s19t37
slug: range-aware-shell-completion
status: pending
---

# Range-aware shell completion

## Context

Split out of [s19t35], which lands range expressions (`s19t10-15,17`) but keeps completion minimal: it emits bare ids, and an `incomplete` containing `-`, `..` or `,` yields no candidates.

Making completion range-aware needs partial-expression parsing, anchor resolution and sibling enumeration inside the completion hot path — a feature in its own right, and bundling it would have made [s19t35]'s diff hard to review.

## Decisions

- Completion should parse the partial expression, resolve its anchor, and offer sibling groups for the trailing element — completing `s19t10-1<TAB>` to `s19t10-15`. Typer replaces the whole word, so the candidate is the full expression, not just the group.

## Open questions

- Whether to reuse the slice-4 grammar parser directly, which would need a lenient/partial-input mode it does not have for command-line use.
- Whether to offer only *existing* siblings as endpoints (consistent with the endpoint-must-exist rule) or any plausible group.
- Completion currently scans only root tasks and their direct subtasks, so deeper anchors (`s19t3502-…`) have no candidates to offer — this may need widening first.
- Latency: completion runs on every `<TAB>` and currently parses every root task file. Anchor resolution for `q`/`p`/`ta` adds `.recent` and todo-list reads.

## Out of scope

- The range grammar itself and its resolution — [s19t35].

