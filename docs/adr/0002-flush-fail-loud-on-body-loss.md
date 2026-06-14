# Flush is fail-loud on body loss; Task schema is strict

A field-contract drift once let a flush silently wipe the [Task body] from every
`##`-structured file it rewrote: an old-shaped parse result constructed the current
`Task` with an `extra_sections=` kwarg, which a lenient pydantic model silently
dropped, leaving `description` empty; the next flush re-rendered and overwrote the
prose. We now bracket the flush at both ends so a future contract or render drift
fails loud instead of destroying data:

- **Strict schema** — `Task` sets `model_config = ConfigDict(extra="forbid")`, so an
  unknown kwarg (the historical `extra_sections`) raises at construction instead of
  being silently discarded. Safe because `Task` is only ever built with explicit
  kwargs (no `model_validate`/dict construction, no subclasses).
- **Round-trip guard** — before writing a file, `_flush_task` re-parses the rendered
  output and compares the body against the in-memory task; whitespace is collapsed on
  both sides so the check tolerates un-normalised in-memory bodies while still
  catching total or partial body loss. On mismatch it raises `TaskValidateError`.

## Consequences

- A flush can now abort mid-iteration. Files written before the failure were each
  verified faithful, so no file is corrupted — the flush is merely incomplete and the
  user is told loudly.
- The guard runs only in the existing "about to write" branch, so unchanged files are
  not re-parsed.

## Considered Options

- **Skip the offending file and continue** — rejected: the guard exists to turn
  silent data loss into a loud failure; swallowing it lets in-memory and on-disk
  state diverge unnoticed.
- **Non-shrink check against the on-disk source** — refuse any write that shrinks the
  body relative to what is on disk. Rejected: false-positives on legitimate body
  deletions (a user clearing the body looks identical), and the construction-time wipe
  is already caught by the strict schema.
