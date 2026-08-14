---
id: s26t1901
slug: amend-adr-0004-with-the
status: pending
---

# Amend ADR 0004 with the action-report format

## Goal

Document the uniform action-report format in ADR 0004
(`docs/adr/0004-commands-speak-json-recent-and-preview.md`) as an authoritative
contract, so the code slices that follow implement a written spec.

## Decisions & constraints

- Amend ADR 0004 (still `status: proposed`), do **not** write a new ADR — 0004
  already owns "how commands report"; a separate record would fragment one
  convention. *Rejected: new ADR 0005.*
- The format: an `<Action>:` header line (e.g. `Adding to TODO:` /
  `Removing from TODO:`), then one bullet per requested ref,
  `- <id>: <title>[  (<outcome>)]`. The trailing `(outcome)` is shown **only when
  it deviates** from the header's implied action — the successful common path has
  no annotation.
- Note this **supersedes contract 3's optional freeform echo** ("a leading
  'doing X with these refs' line") — the action report is the standardised
  replacement.
- Mark `todo`/`untodo` as the **first adopter** and reference the follow-up task
  that migrates the remaining report-and-preview commands.
- Keep 0004 as the single source of truth for command reporting.

## Edge cases

- Preserve the existing four contracts and the accepted-deviations section; this
  is an addition/refinement, not a rewrite.
- Be explicit that the reporter is print-only and callers still own the JSON
  `task_refs` emission (consistent with the existing `print_tree` split).

## Key files

- `docs/adr/0004-commands-speak-json-recent-and-preview.md`

## Acceptance criteria

- ADR 0004 contains the action-report format (header + `- id: title (outcome)`
  bullets, deviation-only annotation).
- It states the format supersedes contract 3's freeform echo.
- It names `todo`/`untodo` as first adopter and links the follow-up migration
  task.
- `uv run tox` passes (docs-only change must not break any environment).
