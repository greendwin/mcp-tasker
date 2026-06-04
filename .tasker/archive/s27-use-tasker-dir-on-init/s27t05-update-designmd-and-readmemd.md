---
id: s27t05
slug: update-designmd-and-readmemd
status: done
---

# Update DESIGN.md and README.md

Bring docs in line with the new default.

## Scope
- `DESIGN.md` §Initialize (around lines 195–205): `tasker init` creates `.tasker/`; legacy `tasker/` is still recognized; user-level path unchanged.
- `README.md`: mirror the change wherever the directory name appears.
- No CONTEXT.md / ADR.

## Done when
- `uv run tox` is green.
- Docs reference `.tasker/` as the new default, mention legacy fallback in one place.
