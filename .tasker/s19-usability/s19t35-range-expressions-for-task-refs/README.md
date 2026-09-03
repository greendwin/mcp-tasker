---
id: s19t35
slug: range-expressions-for-task-refs
status: pending
---

# Range expressions for task refs, and the ref/id/filename split

## Context

A user closing out a story types the same id prefix over and over: `tasker done s19t10 s19t11 s19t12 …`. We want a range expression — `s19t10-15,17` — that names a span of siblings in one token, and the same form on the recent shortcuts (`q`, `p`, `pp`, `t<letter>`).

The obvious separator, `-`, was already the slug delimiter: `parse_task_ref` accepts `s19t35-some-slug` and silently strips the tail. That collision turned out to be a symptom of a deeper conflation — the word *ref* named three different things (canonical identity, on-disk filename stem, and whatever the user typed), so some functions required a bare id and others tolerated a slug tail with no way to tell from a signature. So this task is two things: split those three concepts apart, then build range expressions on the clean foundation.

Recorded as ADR 0005; the glossary gained **Task id**, **Task ref**, **Filename stem**, and **Range expression**; ADR 0004 gained a clarification that a ref may resolve to several ids.

## Decisions

- **Three distinct concepts, three names** — a *task id* (`s19t35`) is the canonical identity and the only currency below the resolution boundary; a *task ref* is whatever the user types at the CLI/MCP boundary and may resolve to many ids; a *filename stem* (`s19t35-slug`) is a filesystem concern only. Shortcuts (`q`, `p03`, `ta`, name matches) mean the ref concept genuinely survives — it just stops being anything but input.

- **Slug refs are rejected on input** — `tasker view s19t35-my-slug` now errors with a targeted message naming the id to use, not a generic parse error. *Rejected: disambiguating by shape (trailing `-<digits>` is a range, anything else a slug) — costs nothing at the boundary and breaks no input, but leaves the ref/id ambiguity in every signature below it, which is the larger problem.* *Rejected: `..` as the sole separator, which sidesteps the collision entirely but makes the common closed range the awkward spelling.* *Rejected: a warn-then-remove deprecation — the shim keeps alive precisely the dual-mode parser this work exists to delete.*

- **`Task.ref` → `Task.filename_stem`**, and every `task_ref` parameter below `resolve_ref` renamed to `task_id`, so a surviving `task_ref` deep in the call graph is a grep-able defect. Filename construction stays behind a property rather than being scattered across the loader.

- **JSON keys become `task_id` / `task_ids`**, values are ids. *Rejected: keeping `task_ref`/`task_refs` (enshrines the confusion) and emitting both as aliases (doubles every payload to protect a contract nobody pinned).* No persisted schema, so compat cost is near zero.

- **Result lines print ids, not slug refs** — ADR 0004 already required authoritative result reporting to use final ids, so the ~20 `Task {task.ref} {action}` lines were already out of line.

- **A range expression addresses exactly one sibling set.** The base names an *anchor* and the digit groups enumerate that anchor's children: `s19t10-15` → anchor `s19`; `s19t3502-05` → anchor `s19t35`; `s01-05` → root level; `q10-15` → children of recent; `p10-15` → siblings of recent. Cross-parent forms like `s19t10,s20t01` are rejected — pass a second argument instead. Shortcut anchors come for free from the existing `qNN`/`pNN` semantics.

- **Groups are always a single digit group**, run through the existing `normalize_id_digits`: `s19t1-5` and `s19t01-5,7` work; a 4-digit endpoint like `s19t3502-3505` is a hard error. *Rejected: length-matched widths and full-id endpoints — each adds a parsing mode whose only payoff is saved keystrokes, and both break the requirement that `-` and `,` elements read identically.*

- **`-` and `..` are interchangeable for closed ranges; only `..` may be left open** — `s19t10..`, `s19t..15`, `s19t..` (all children of `s19`); `s19t10-` errors and suggests `..`. The asymmetry is the mnemonic: if it's open, it's dots. Open ranges knowingly reintroduce unbounded selection, so the base must always be explicit.

- **Descending ranges are ill-formed** (`s19t10-7` errors); `s19t10-10` is a legal one-element range.

- **Expansion filters the anchor's real children, ascending by id.** Interior gaps are skipped silently — sibling numbering is sparse in practice — but both *written* endpoints must exist, which catches the fat-finger `-99` and the stale-id paste. *Rejected: generate-and-require-all, defeated by any real tree.* Ascending id (not repo sibling order) because `tasker order s19t10-15` must not expand according to the very order key it is about to rewrite.

- **Status-blind, archive-aware.** Done and cancelled siblings are included — the action report's `(already done)` annotation is exactly how those get reported — but a range only enumerates the anchor's own archive partition, since archived roots are hidden from `list` and must not be swept into a mutation invisibly. *Rejected: command-sensitive expansion, which would make one expression mean different sets per verb.*

- **Available everywhere; arity enforced at single-ref call sites.** The mental model is "a ref may name several tasks", full stop. `view`, `edit`, `add <parent>`, `move --attach` and the MCP mutators raise a counting error ("selected 6 tasks, expected 1"). *Rejected: making range syntax a parse error on single-ref parameters, which forces users to memorise the grammar per command.*

- **One report bullet per resolved id** — expansion is invisible in output; `done s19t10-15` reads as if the six ids were typed. Keeps ADR 0004's `(outcome)` deviation annotations working, which a grouped bullet could not.

- **MCP is not blocked, just not advertised.** Range expressions and shortcuts still resolve if passed, but the shared `task_ref` description tells agents to pass a user's shorthand through verbatim rather than resolve it themselves, and never to *construct* recent-shortcuts, which resolve against `.recent` — state that per ADR 0004 MCP calls do not update. *Rejected: silence (costs a round trip and makes agents guess) and full advertisement (the schema note is the only place an agent learns constructing `q` is unsafe).*

- **Completion emits bare ids**, with the title still serving as the description, so the slug's informational value is not lost.

## Open questions

- Whether open-ended ranges want any guard against very large selections — deferred; the explicit-base requirement is the only mitigation for now.

## Out of scope

- Batch-aware shell completion (completing `s19t10-1<TAB>` → `s19t10-15`) — needs partial-expression parsing and anchor resolution in the completion path; filed separately.
- Widening the MCP mutators to accept several ids per call — an agent-facing schema change with its own return-shape questions; filed separately.
- `view` fanning out over a range to print several tasks — makes the `--json-output` shape depend on the ref, cutting against ADR 0004's uniform-payload contract.

## Subtasks

- [ ] [s19t3501](s19t3501-ids-are-what-we-print.md): Ids are what we print and emit
- [ ] [s19t3502](s19t3502-reject-slug-refs-on-input.md): Reject slug refs on input
- [ ] [s19t3503](s19t3503-rename-task-ref-to-task.md): Rename task_ref to task_id below the resolution boundary
- [ ] [s19t3504](s19t3504-range-expression-grammar-parser.md): Range-expression grammar parser
- [ ] [s19t3505](s19t3505-resolve-range-expressions-against-the.md): Resolve range expressions against the task tree
- [ ] [s19t3506](s19t3506-document-the-range-expression-language.md): Document the range-expression language
