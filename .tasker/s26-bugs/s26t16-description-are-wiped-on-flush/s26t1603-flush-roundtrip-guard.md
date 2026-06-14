---
id: s26t1603
slug: flush-roundtrip-guard
status: pending
---

# Flush round-trip guard

## Goal

A flush that would write a file losing body content raises `TaskValidateError` and leaves the existing file untouched, instead of silently overwriting prose. This brackets the *serialization* end of the flush.

## Decisions & constraints

- In `_flush_task` (`src/tasker/repo/_task_loader.py`), inside the existing "about to write" branch (the `if orig is None or new_filename != orig.filename or rendered != orig.content:` block, before `write_text`), re-parse the just-rendered output and compare its body to the in-memory task.
- **Invariant = render-faithfulness:** compare the model against its own serialization (`parse(render(task)).description` vs `task.description`), NOT against on-disk content. False-positive-free and complements `extra="forbid"`. *Rejected: non-shrink check vs on-disk source — false-positives on legitimate body deletions (a user clearing the body looks identical), and construction-time wipe is already caught by the strict schema.*
- **Comparison = normalized-content equality:** collapse whitespace on both sides with `re.sub(r"\s+", " ", x).strip()` before comparing (treat `None`/empty as `""`). Catches total AND partial body loss; tolerates un-normalized in-memory bodies (e.g. from `edit_task`) so no whitespace false positives. *Rejected: exact equality (whitespace false positives); emptiness-only (misses partial-section loss).*
- **Failure action = raise** `TaskValidateError`, aborting the flush loud. *Rejected: skip-and-continue — lets in-memory/on-disk state diverge unnoticed.* Files written before the failure were each verified faithful, so none are corrupted — the flush is merely incomplete.
- **Placement:** only in the about-to-write branch so unchanged files are not re-parsed.
- Re-parse uses the existing `parse_task(rendered, task_id=..., slug=..., extended=...)` path (returns the body via `description`); reuse `task.id`/`task.slug`/`task.extended`.

## Edge cases

- New task (`orig is None`) with a faithful body → guard passes harmlessly.
- Empty body in, empty body out → passes (both collapse to `""`).
- On guard failure the existing on-disk file must NOT be overwritten/truncated.

## Testing

- Monkeypatch `tasker.repo._task_loader.render_task` to return body-stripped output (per project convention: `monkeypatch`, never `mock.patch`). Build a task with a non-empty body, call `flush_to_disk`, assert it raises `TaskValidateError` and the on-disk file is left intact.
- Happy-path test: a normal non-empty body flushes without raising.

## Key files

- `src/tasker/repo/_task_loader.py` (`_flush_task`; imports `render_task`, `parse_task`, `TaskValidateError`)
- `src/tasker/parse.py` (`parse_task`)

## Acceptance criteria

- With a lossy (body-stripping) renderer, `flush_to_disk` raises `TaskValidateError` and the prior file content is preserved on disk.
- A normal flush with a non-empty `##`-structured body succeeds and writes faithfully.
- Whitespace-only differences between in-memory and re-parsed body do NOT trip the guard.
