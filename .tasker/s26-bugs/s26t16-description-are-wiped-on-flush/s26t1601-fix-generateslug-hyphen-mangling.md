---
id: s26t1601
slug: fix-generateslug-hyphen-mangling
status: done
---

# Fix generate_slug hyphen mangling

## Goal

`generate_slug` treats internal punctuation (especially `-`) as a word separator instead of deleting it, so hyphenated titles produce correct kebab-case slugs and filenames.

## Decisions & constraints

- Reuse `normalize_slug` (in `parse.py`) as the single source of truth for kebab-casing, while preserving `generate_slug`'s distinguishing behavior (cap at 5 words):

  ```python
  def generate_slug(title: str) -> str:
      return "-".join(normalize_slug(title).split("-")[:5])
  ```

- The current bug: `re.sub(r"[^a-z0-9\s]", "", title.lower())` deletes internal punctuation, so `Safe-reattach by content search` → `safereattach-by-content-search`. `normalize_slug` already correctly maps `[^a-z0-9]+` runs → `-`.
- Behavior shift to accept: hyphenated source words now consume more of the 5-part budget — `Safe-reattach by content search` → `safe-reattach-by-content-search` (5 parts), not the old 4-part form. This is the intended correction.

## Edge cases

- Empty / punctuation-only title (`""`, `"---"`) → `""` (matches old behavior).
- Titles longer than 5 words still cap at 5 parts.
- Multi-word + hyphen mix (e.g. `Extract shared skill-dir overwrite primitive` → `extract-shared-skill-dir-overwrite` after the 5-part cap).

## Key files

- `src/tasker/repo/_utils.py` (`generate_slug`, line ~15)
- `src/tasker/parse.py` (`normalize_slug`, reused)

## Acceptance criteria

- A hyphenated title yields a slug that preserves the hyphen as a separator (`safe-reattach-by-content-search`).
- The 5-part cap still applies after normalization.
- Empty/punctuation-only titles yield `""`.
