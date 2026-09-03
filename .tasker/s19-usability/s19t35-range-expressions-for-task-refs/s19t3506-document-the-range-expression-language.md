---
id: s19t3506
slug: document-the-range-expression-language
status: pending
---

# Document the range-expression language

## Goal

DESIGN.md documents range expressions alongside the existing shortcut table, and MCP tool schemas tell agents how to treat user shorthand.

## Decisions & constraints

- The grammar is a **user-facing reference, not an ADR** — reversible and unsurprising, unlike the ref/id split which is recorded in ADR 0005. *Rejected: a second ADR for the selection language, whose entire content would be "see the reference docs".*
- DESIGN.md's "Recent task shortcuts" section already has a shortcut table; range expressions extend it rather than starting a rival section. Document the anchor rule (base names an anchor, groups enumerate its children), the `-`/`..` split with open ranges dots-only, single-digit-group padding, endpoint-must-exist, ascending-id expansion, and status-blind/archive-aware scope.
- DESIGN.md's line about single-digit padding and odd-length rejection already exists and now also governs range groups — extend it rather than restating.
- The slug-ref removal is a **breaking change** on a `1.8.1` package: DESIGN.md's note that `s01t01-define-task-forms` is accepted with "slug portion ignored for lookup" must go, and the change needs an explicit "Breaking" line at the next `/prepare-release`.
- **MCP: not blocked, just not advertised.** A scoped note on the shared `task_ref` description, split by kind because the two shorthands carry different risk:
  > If the user refers to a task by shorthand (`q`, `p03`, `ta2`, or a range like `s19t10-15`), pass it through verbatim rather than resolving it yourself. Do not construct recent-shortcuts (`q`/`p`/`t<letter>`) on your own — they resolve against user-local state that MCP calls do not update.

  Rationale: when the user says "start ta1", pass-through is strictly better than agent-side resolution, which costs a `list` round trip and re-introduces the same staleness race with an extra step. But an agent *constructing* `q` is wrong by construction — ADR 0004 contract 1 forbids MCP mutators from writing `.recent`, so `q` still points at whatever the human last touched. Range expressions carry no hidden state, so constructing those is harmless. *Rejected: saying nothing (pushes agents toward the worse behaviour) and advertising both without the caveat (the schema note is the only place an agent learns constructing `q` is unsafe).*
- Set ADR 0005's status to `accepted` once slices 1–5 have landed.

## Edge cases

- `docs/agents/task-tracker.md` documents MCP calls with `task_ref: <id>` — those are boundary declarations and stay named `task_ref`, but check the prose does not imply slug refs are acceptable.
- README may carry CLI examples using slug refs.
- The MCP note must be short: it is repeated across every tool that takes a `task_ref`, so length has a real token cost for agents.

## Key files

- `DESIGN.md` (shortcut table ~line 408-428; the ref-forms list ~line 82)
- `docs/adr/0005-refs-are-human-input-ids-are-identity.md` (status → accepted)
- `README.md`
- `src/tasker/mcp/*.py` (shared `task_ref` parameter description)
- `docs/agents/task-tracker.md`

## Acceptance criteria

- DESIGN.md documents the anchor rule with worked examples for `s19t10-15`, `s19t3502-05`, `s01-05`, `q10-15`, `p10-15`, `ta02-04`.
- DESIGN.md states that `-` and `..` are interchangeable when closed and that only `..` may be open.
- DESIGN.md no longer claims the slug portion of a ref is accepted and ignored.
- Every MCP tool exposing `task_ref` carries the shorthand note.
- ADR 0005 status is `accepted`.
- `uv run tox` clean.
