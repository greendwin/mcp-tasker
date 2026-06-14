---
id: s26t16
slug: description-are-wiped-on-flush
status: done
---

# Description are wiped on flush

## Context

A single `flush_to_disk` (triggered by an unrelated status change) re-rendered every task file it loaded and stripped the free-form prose body from each file whose body was made of `##` sections. Root cause was a cross-version contract drift: an old-shaped parse result constructed the current `Task` with an `extra_sections=` kwarg, which the lenient pydantic model silently dropped, leaving `description` empty; the next render+flush overwrote the prose. ADR 0001 already removed `extra_sections` from the model, so this exact path can no longer recur in a single-version round-trip. This task is therefore **hardening** — make a future contract or render drift fail loud instead of silently destroying bodies — plus fixing the one genuinely-live bug (`generate_slug` mangling hyphenated titles).

See `docs/adr/0002-flush-fail-loud-on-body-loss.md`.

## Decisions

- **Strict Task schema** — set `model_config = ConfigDict(extra="forbid")` on `Task` so an unknown kwarg (the historical `extra_sections`) raises at construction instead of being silently discarded. Safe: `Task` is only ever built with explicit kwargs (no `model_validate`/dict construction, no subclasses). This brackets the *construction* end of the flush.
- **Flush round-trip guard** — in `_flush_task`, before writing, re-parse the rendered output and compare its body against the in-memory task; on body loss, raise `TaskValidateError`. This brackets the *serialization* end. *Rejected: non-shrink check against the on-disk source — false-positives on legitimate body deletions (a user clearing the body looks identical), and the construction-time wipe is already caught by the strict schema.*
- **Guard invariant = render-faithfulness** — compare model ⟷ its own serialization, not against on-disk content. False-positive-free and complements `extra="forbid"`.
- **Comparison = normalized-content equality** — collapse whitespace on both sides (`re.sub(r"\s+", " ", x).strip()`) before comparing. Catches total AND partial body loss; tolerates un-normalized in-memory bodies (e.g. from `edit_task`) so no whitespace false positives. *Rejected: exact equality (false-positives on whitespace); emptiness-only (misses partial-section loss).*
- **Failure action = raise** — `TaskValidateError`, aborting the flush loud. Files written before the failure were each verified faithful, so none are corrupted — the flush is merely incomplete and the user is told. *Rejected: skip-and-continue — lets in-memory and on-disk state diverge unnoticed, defeating the guard's purpose.*
- **Guard placement** — runs only inside the existing "about to write" branch (right before `write_text`), so unchanged files are not re-parsed.
- **`generate_slug` hyphen fix** — `return "-".join(normalize_slug(title).split("-")[:5])`. Reuse `normalize_slug` as the single source of truth for kebab-casing while keeping the 5-part cap. Treats `-` as a word separator instead of deleting it (`Safe-reattach by content search` → `safe-reattach-by-content-search`, not `safereattach-by-content-search`).

## Open questions

- None.

## Out of scope

- Restart-after-upgrade / stale-process operational guidance — operational, not a code change.
- Recovery of already-wiped bodies — a manual `git restore` concern, separate from the code fixes here.

## Subtasks

- [x] [s26t1601](s26t1601-fix-generateslug-hyphen-mangling.md): Fix generate_slug hyphen mangling
- [x] [s26t1602](s26t1602-strict-task-schema-extraforbid.md): Strict Task schema (extra=forbid)
- [x] [s26t1603](s26t1603-flush-roundtrip-guard.md): Flush round-trip guard
