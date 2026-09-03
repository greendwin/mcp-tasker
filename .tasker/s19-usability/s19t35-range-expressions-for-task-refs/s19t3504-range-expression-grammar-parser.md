---
id: s19t3504
slug: range-expression-grammar-parser
status: pending
---

# Range-expression grammar parser

## Goal

A pure parser turning a range expression such as `s19t10-15,17` into an anchor plus an ordered list of digit groups, with no repository access.

## Decisions & constraints

- Deep module: all grammar complexity behind a simple interface, unit-testable with zero filesystem or repo. Resolution against the tree is slice 5's job.
- **One anchor, one sibling set.** The base names an anchor and every group enumerates that anchor's children. Cross-parent forms like `s19t10,s20t01` are **rejected** — a user can always pass a second argument.
- Grammar shape:
  ```
  expression := base group (('-'|'..') group)? (',' group (('-'|'..') group)?)*
  group      := digits          # one sibling digit group
  base       := 's' | 's19t' | 's19t35' | 'q' | 'p' | 'pp' | 't<letter>' | ...
  ```
  A lone group like `17` is a one-element range, which is why the form is called a *range expression* rather than a batch/selection.
- **Groups are always a single digit group**, run through the existing `normalize_id_digits`: `s19t1-5` → `01`–`05`, `s19t01-5,7` valid, odd-length runs longer than one digit still rejected as ambiguous. A 4-digit endpoint (`s19t3502-3505`) is a hard error: *"range endpoint must be a single digit group"*. *Rejected: length-matched widths, and accepting a full sibling id as endpoint (`s19t3502-s19t3505`)* — each adds a parsing mode whose only payoff is saved keystrokes, and both break the requirement that `-` and `,` elements read identically.
- **`-` and `..` are interchangeable for closed ranges; only `..` may be left open.** `s19t10..`, `s19t..15`, `s19t..` are open forms. `s19t10-` is an error that suggests `..`. The asymmetry is the mnemonic — "if it's open, it's dots" — and is easier to remember than two fully interchangeable separators. *Rejected: `..` only (makes the common closed form the awkward spelling) and `-` only (no open ranges, so no whole-sibling-set selector).*
- **Descending is ill-formed** — `s19t10-7` errors. `s19t10-10` is a legal one-element range.
- The base must always be explicit; there is no way to write "everything everywhere". Open ranges knowingly reintroduce unbounded selection and this is the only mitigation.

## Edge cases

- `s19t10-15` must parse as anchor `s19` + groups `10..15` (last group stripped from the base), while `s01-05` is anchor = root level and `s19t3502-05` is anchor `s19t35`.
- Shortcut bases (`q`, `p`, `pp`, `t<letter>`) carry no digits of their own before the first group: `q10-15` is anchor `q`, groups `10..15`. `q` alone is not a range expression.
- A plain id with no separators (`s19t10`) must still parse — the parser is on the common path, so a non-range ref cannot become slower or error.
- `s19t10-20` where the tail is all digits must be read as a range, not as the slug error from slice 2.
- Mixed separators in one expression (`s19t01-05,10..15`) — decide and test; the grammar as written permits it.
- Empty groups (`s19t,05`, `s19t01,,05`) and a trailing comma must error cleanly.

## Key files

- New module under `src/tasker/` for the grammar (kept private per the project's `_`-prefixed submodule convention)
- `src/tasker/parse.py` (`normalize_id_digits` is reused as-is)
- New test module, e.g. `tests/test_range_expression.py`

## Acceptance criteria

- `s19t10-15,17` parses to anchor `s19` with groups `10,11,12,13,14,15,17` (or an equivalent range representation preserving order).
- `s19t1-5` and `s19t01-5,7` parse with groups zero-padded.
- `s19t3502-3505` errors mentioning a single digit group.
- `s19t10-` errors and the message suggests `..`.
- `s19t10-7` errors as ill-formed.
- `s19t..`, `s19t10..`, `s19t..15` parse as open forms.
- `s19t10,s20t01` is rejected.
- `s19t10` (no separators) parses as a single-group expression.
- No repo, filesystem, or `pyfakefs` fixture is needed by any test in this module.
