---
id: s19t2704
slug: generalize-error-message-and-update
status: done
---

# Generalize error message and update DESIGN.md + README.md

Rename the ambiguous-digits error from `Ambiguous shortcut digits {ref!r}` to `Ambiguous digits in task ref {ref!r}` so it reads correctly for both shortcut and direct-ref paths; update any existing tests that match on the old wording.

Docs:

- `DESIGN.md:409` — extend the existing padding sentence to mention direct refs alongside `q3` / `ta3`.
- `README.md:246` — same: include `s1` → `s01` and `s2t2` → `s02t02` examples.
