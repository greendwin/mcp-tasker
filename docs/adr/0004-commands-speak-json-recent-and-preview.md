---
status: proposed
---

# Every task-facing command speaks JSON, updates `.recent`, and previews what it changed

Every public CLI command — and its MCP twin — that reads or manipulates tasks
MUST honour four cross-cutting contracts rather than treating them as
per-command choices:

1. **Update `.recent`** — call `save_recent_for_refs(repo, …)` with the tasks it
   touched, so the next bare `list`/`view` lands on what the user just worked on.
   `.recent` stores the *common ancestor* of the referenced tasks, so refs must be
   passed **after** any relocation/rename — the stored ancestor must reflect the
   tasks' final ids, not their pre-move ids.
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
   result report and is exempt from the final-id rule. Commands that mutate a task
   *in place* without moving it (`edit`, `start`, `review`, status changes) may
   show a lighter task-level preview instead — see the accepted deviations below.

A new command that skips any of these is a defect, not a stylistic variation;
reviewers check all four.

## Scope, exemptions, and accepted deviations

Exempt commands: `resolve` (git-merge conflict resolver — no task refs, no repo)
and `mcp` (starts the server). Everything else is in scope.

One in-scope command is actively being brought into compliance:

- **`order`** — no `--json-output` payload on its main result line (only its
  "Renamed tasks" sub-output carries `context`); `.recent` was written from
  *pre-relocation* ids. Closed by the `s28t05` batch: `.recent` and the json
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
