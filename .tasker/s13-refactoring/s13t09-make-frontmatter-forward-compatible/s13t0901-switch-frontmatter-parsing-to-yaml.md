---
id: s13t0901
slug: switch-frontmatter-parsing-to-yaml
status: in-progress
---

# Switch frontmatter parsing to YAML

## Goal

The front-matter block is parsed with `yaml.safe_load` instead of the
line-by-line scanner. Rich YAML syntax works for the owned keys (`id`, `slug`,
`status`, `order`): quoted values, flexible whitespace. Unknown keys still raise
the existing "Unknown front-matter field" `TaskValidateError` at this slice.
Existing task files parse and render byte-identically.

## Decisions & constraints

- Add **PyYAML** as a runtime dependency (`pyproject.toml`); use `safe_load`
  only. Rejected: ruamel.yaml (comment fidelity is marginal for machine-managed
  files; its round-trip objects would leak into the model) and verbatim raw-line
  preservation (cannot support data-level guarantees later).
- Owned keys keep their exact validation semantics: unknown `status` value and
  non-int `order` raise `TaskValidateError` with the same task_ref context as
  today. `slug` still goes through `normalize_slug`; empty slug → None.
- New error cases, all `TaskValidateError`: front-matter block is invalid YAML;
  block parses to a non-mapping (list/scalar). Existing missing/unclosed `---`
  errors unchanged.
- Rendering is untouched — `task.md.j2` remains the single source of truth for
  owned-field output; no cosmetic churn on any existing file.

## Edge cases

- YAML type coercion: `status: pending` loads as str, but `order: 5` as int and
  a quoted `order: "5"` as str — accept both int and digit-string for order,
  reject the rest.
- YAML `null` / empty value for `slug:` (→ None) and for `status:`
  (→ TaskValidateError or default pending — match current behavior: current
  code would raise on empty `TaskStatus("")`, keep raising).
- Duplicate keys in the block (PyYAML keeps the last) — acceptable, no special
  handling.
- Values that YAML mangles vs the old scanner (e.g. unquoted `slug: 03-fix` is
  str, fine; `id` values are plain strings).

## Key files

- `src/tasker/parse.py` — `_parse_content` frontmatter section
- `pyproject.toml` — add `pyyaml` dependency
- `tests/test_parse.py` — parser behavior tests

## Acceptance criteria

- A frontmatter block with quoted/spaced YAML values for owned keys parses to
  the same `Task` as the plain form.
- Invalid YAML and non-mapping blocks raise `TaskValidateError` naming the task.
- Unknown keys still raise "Unknown front-matter field".
- All existing parse/render/merge tests pass unchanged.
- `uv run tox` passes (all environments).
