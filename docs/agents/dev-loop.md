# Dev loop

This repo runs inside **Claude Code**. The code-review lens invokes the built-in
`/code-review` command (read-only by default); the refactor lens runs the built-in
`/simplify` in a **throwaway scratch worktree** and captures the diff it produces as
its proposal — `/simplify` never touches the tracked tree, so `dev-loop`'s
single-writer invariant holds (only `tdd` applies the accepted hunks). Each lens below
is one reviewer; `dev-loop` spawns the lenses in a roster in parallel and collects
their findings. This document is self-contained — no other file is needed to perform
any lens below.

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

### simplify

Create a **throwaway scratch worktree** of the change under review, run the built-in
`/simplify` inside it, and **capture the diff it produces**. Write that diff to the
scratch-file path `dev-loop` gave you and report the finding **by reference**: set
`patch-ref` to that path and `blast-radius` to the files touched plus lines added/
removed — return **no hunks inline**. Then discard the worktree without touching the
tracked tree. Propose only: you never write the tracked tree — `dev-loop` hands the
`patch-ref` to `tdd`, which reads it and applies the hunks verbatim (repairing or
dropping any that redden the suite).
