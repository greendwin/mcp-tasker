---
status: proposed
---

# Every task-facing command speaks JSON, updates `.recent`, and previews what it changed

Every public CLI command — and its MCP twin — that reads or manipulates tasks
MUST honour four cross-cutting contracts rather than treating them as
per-command choices:

1. **Update `.recent`** — **CLI only.** A CLI command calls
   `save_recent_for_refs(repo, …)` with the tasks it touched, so the next bare
   `list`/`view` lands on what the user just worked on. `.recent` stores the
   *common ancestor* of the referenced tasks, so refs must be passed **after** any
   relocation/rename — the stored ancestor must reflect the tasks' final ids, not
   their pre-move ids. **MCP twins MUST NOT touch `.recent`.** It is a
   human-interaction affordance — it steers where an interactive user's next bare
   `list`/`view` lands — and an agent driving the MCP tools must not silently
   move that pointer out from under the user. An MCP mutator that writes `.recent`
   is a defect.
2. **Support `--json-output`** — every user-visible result line carries a
   `context=` payload (`JsonAppend` / `set_context`), so the same command emits a
   structured object under `--json-output` instead of prose. A command whose
   result is human-only text is incomplete: an agent driving the CLI cannot read
   it.

Every command that changes a task's **position** in the tree (move, order,
promote, relocate, todo) additionally MUST, on success:

3. **Highlight the affected tasks** and **preview them in the updated
   hierarchy** — via `print_parent_preview(repo, *affected)`, which renders each
   touched task with `highlight=True` inside its post-change parent tree. The
   **authoritative** result reporting — the rename listing, the preview tree, and
   the `--json-output` payload — must reference tasks by their **final** ids. A
   command may *additionally* echo the command as typed (a leading "doing X with
   these refs" line naming the user's original, pre-move ids); that echo is not a
   result report and is exempt from the final-id rule. **This optional freeform
   echo is superseded by the action-report format** — see
   [The action-report format](#the-action-report-format) below, which
   standardises that leading block. Commands that mutate a task
   *in place* without moving it (`edit`, `start`, `review`, status changes) may
   show a lighter task-level preview instead — see the accepted deviations below.

A new CLI command that skips any of these is a defect, not a stylistic variation;
reviewers check all four. An MCP twin returns a structured ack instead of a
preview and, per contract 1, leaves `.recent` untouched.

## The action-report format

Report-and-preview commands MUST precede their preview with a uniform **action
report** — a print-only block that names, per requested ref, what the command
did. This is the standardised replacement for contract 3's optional freeform
echo (the leading "doing X with these refs" line), which it **supersedes**:
commands report through the action report, not through ad-hoc echo or per-ref
confirmation sentences.

**Format.** An `<Action>:` header line naming the operation, then one bullet
per requested ref:

    <Action>:
    - <id>[  (<outcome>)]

Bullets carry the ref's id only — no title; the preview that follows renders
titles. The trailing `(<outcome>)` is shown **only when the outcome deviates** from the
header's implied action. The successful common path carries no annotation — a
bullet with no `(outcome)` means "the header's action happened as stated"; only
deviations (a no-op, a warning) are annotated. Notes about the overall
*resulting state* are not per-ref outcomes — they are reported outside the
bullet list.

**Duplicates are ignored.** Requested refs are deduplicated by *resolved task
id* before processing, keeping first-occurrence order: a repeated ref yields
one bullet, one `task_refs` JSON entry, and one application of the action — a
duplicate is not a deviation (never annotated as `(already …)` / `(was not …)`).
This rule applies to every command adopting the action report —
`todo`/`untodo` are the first adopters; the remaining report-and-preview
commands pick it up as they migrate to the format.

**Print-only; callers own JSON.** The reporter renders human text only: it is
silent under `--json-output` and emits nothing structured. Each command keeps
owning its `--json-output` contract (contract 2) unchanged — the action report
affects the human rendering only.

## Scope, exemptions, and accepted deviations

Exempt commands: `resolve` (git-merge conflict resolver — no task refs, no repo)
and `mcp` (starts the server). Everything else is in scope.

One in-scope command is actively being brought into compliance:

- **`order`** — no `--json-output` payload on its main result line (only its
  "Renamed tasks" sub-output carries `context`); `.recent` was written from
  *pre-relocation* ids. Since brought into compliance: `.recent` and the json
  `task_refs`/`renames` now carry final ids, while the leading summary line stays
  a deliberate echo of the refs as typed (see contract 3).

The following current behaviours are **accepted deviations**, not defects —
recorded so they are not mistaken for bugs and "fixed":

- **`archive`** — does not update `.recent`. Archiving moves a story *out* of the
  active view, so pointing recent at a just-archived task would be misleading;
  leaving recent where it was is intended. Its counterpart `unarchive` — which
  brings a story back into scope — *does* update `.recent`.
- **`add-many`** — no highlight / hierarchy preview of the created subtasks. It is
  a bulk primitive whose value is throughput; a full per-task preview would bury
  its output.
- **`edit` / `start` / `review`** — show the mutated task via
  `print_task(preview=True)` rather than the highlighted parent tree
  (`print_parent_preview`) used by `reset` / `cancel` / `done`. These commands act
  on a single task in place without moving it, so a task-level preview is
  sufficient; the heavier hierarchy preview is reserved for commands that change a
  task's *position*.

## Considered options

- **Per-command opt-in** — add JSON / recent / preview wherever it "seems
  useful". Rejected: an audit found silent, inconsistent gaps. The value of these
  behaviours is precisely that they are *uniform* — a caller or agent can rely on
  every task-facing command updating `.recent`, emitting JSON, and previewing its
  effect. Opt-in erodes that guarantee one forgotten command at a time.
