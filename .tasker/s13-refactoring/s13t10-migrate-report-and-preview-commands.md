---
id: s13t10
slug: migrate-report-and-preview-commands
status: pending
---

# Migrate report-and-preview commands to the action-report format

## Context

Follow-up to s26t19, which piloted the uniform action-report format
(`<Action>:` header + `- <id>: <title>[  (<outcome>)]` bullets, deviation-only
annotation) on `todo`/`untodo`, added the reusable `ActionReportConfig` /
`print_action_report` reporter in `_print_utils.py`, and documented the format in
ADR 0004. This task migrates the remaining report-and-preview commands to that
same format so every command reports uniformly.

## Scope

Migrate each of these to build an `ActionReportConfig` + `print_action_report`
before their hierarchy/task preview, replacing ad-hoc per-ref confirmation lines
and freeform echo lines (ADR 0004 contract 3):

- `done`, `cancel`, `reset` (status commands)
- `move`, `order`, `unarchive` (organize commands)
- `new`, `add` (create commands)

## Constraints

- Reuse the `s26t19` reporter (`_print_utils.ActionReportConfig` /
  `print_action_report`) — no new rendering mode.
- Preserve each command's existing JSON contract (`task_refs`/`renames`/etc.);
  the reporter is print-only, callers keep emitting their own JSON context.
- Honour ADR 0004's accepted deviations (e.g. `add-many` stays a bulk primitive
  with no per-task preview; `archive` still does not touch `.recent`).
- Outcome annotations only where an outcome deviates from the header's implied
  action (e.g. forced cascades, no-ops, rename mappings).
- Per-command final-id rules from ADR 0004 (move/order report final ids) still
  apply.

## Out of scope

- Any behavioural change beyond the report format (no new flags, no changed
  preview trees).

## Acceptance criteria

- Each listed command emits the uniform action report before its preview.
- Existing JSON-output tests for those commands pass unchanged.
- ADR 0004's first-adopter note is updated to reflect full adoption.
- `uv run tox` passes (all environments).
