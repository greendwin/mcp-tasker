---
id: s26t1602
slug: strict-task-schema-extraforbid
status: done
---

# Strict Task schema (extra=forbid)

## Goal

Constructing a `Task` with an unknown field (e.g. the historical `extra_sections=`) raises immediately at construction instead of silently dropping it — turning a contract drift into a loud failure.

## Decisions & constraints

- Add `model_config = ConfigDict(extra="forbid")` to the `Task` pydantic model.
- Safe to do: `Task` is only ever built with explicit kwargs — verified there are no `Task` subclasses and no `model_validate`/`parse_obj`/dict construction anywhere in `src/tasker/`. So only a genuinely-unknown kwarg would raise.
- This brackets the *construction* end of the flush (the complement to the round-trip guard, which brackets the serialization end). The original data loss happened because the lenient model silently accepted and discarded `extra_sections=`.

## Edge cases

- Existing valid `Task(...)` construction sites must all still pass — none currently pass unknown kwargs, so no production code change beyond the model config.
- Confirm `tox` (mypy/lint/test) stays green; `ConfigDict` import from pydantic.

## Key files

- `src/tasker/base_types.py` (`Task` model; add `from pydantic import ConfigDict`)

## Acceptance criteria

- `Task(id=..., title=..., extra_sections="x")` raises a pydantic `ValidationError`.
- A normal `Task(...)` with only known fields constructs successfully.
- Full `tox` passes.
