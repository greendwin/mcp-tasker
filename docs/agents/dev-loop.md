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

### thermo-nuclear-code-quality-review

Invoke the `thermo-nuclear-code-quality-review` skill over the whole change for an
extremely strict maintainability and structure audit. Be ambitious: hunt for "code
judo" restructurings that preserve behavior while making whole branches, helpers,
modes, or layers disappear entirely — prefer deleting complexity over rearranging it.
Flag, as distinct findings: any file the change pushes past ~1000 lines without a
strong structural reason; ad-hoc conditionals or one-off special cases tangled into
unrelated flows (spaghetti growth); thin or pass-through abstractions and identity
wrappers that add indirection without buying clarity; and type/boundary smells —
needless optionality, `any`/cast-heavy code, or silent fallbacks papering over an
unclear invariant. Report each as a finding with location, rationale, and an inline
`suggested-fix`. Do not edit code; propose only.
