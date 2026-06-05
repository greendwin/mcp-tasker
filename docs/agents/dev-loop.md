# Dev loop

This repo runs inside **Claude Code**. The code-review lens invokes the built-in
`/code-review` command (read-only by default); the refactor lenses are read-only
reviewers that propose refactorings in prose. Every lens reports findings with an
inline `suggested-fix` and never edits the tracked tree — `dev-loop` hands the accepted
findings to `tdd`, the sole writer, which implements them under green tests. Each lens
below is one reviewer; `dev-loop` spawns the lenses in a roster in parallel and
collects their findings. This document is self-contained — no other file is needed to
perform any lens below.

## `code-reviewer`

Runs against the implemented change once it is green.

### general

Invoke the `/code-review` built-in command over the change under review. Report every
issue it surfaces — correctness, missing/weak tests, security, and maintainability —
as findings. Do not edit code; propose only.

### tests

Review the change specifically for test quality: every new public behavior has a
behavior-level test, tests exercise the public interface (not internals), and there
are no implementation-coupled or mock-heavy tests. Report gaps and weak tests as
findings. Do not edit code; propose only.

## `refactor-reviewer`

Runs against the whole change during the refactor phase.

### duplication

Review the change for repeated logic or structure — copy-pasted blocks, parallel
branches that differ only in a value, the same computation done in several places.
For each, name the duplicated sites and propose how to unify them (extract a helper,
parameterize, hoist a shared value). Report each as a finding with location, rationale,
and an inline `suggested-fix`. Do not edit code; propose only.

### deep-modules

Review the change for shallow modules — a large interface over thin implementation,
pass-through wrappers, and abstractions that leak their internals. Propose how to make
the module deeper: collapse a needless wrapper, hide complexity behind a smaller
interface, or fold a one-call helper into its caller. Report each as a finding with
location, rationale, and an inline `suggested-fix`. Do not edit code; propose only.

### simplification

Review the change for control-flow complexity — deep nesting, arrow code, redundant
conditionals, and branches that a guard clause or early return would flatten. Propose
the flattened form. Report each as a finding with location, rationale, and an inline
`suggested-fix`. Do not edit code; propose only.
