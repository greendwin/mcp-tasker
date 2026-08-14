# Order lives in front matter; ordering a task materializes it as a file

Tasks carry an optional [Order] — a per-sibling-set sort key that expresses
implementation order. Order is stored as an `order:` integer in a task's YAML
front matter, and only file-based tasks (basic/extended) have front matter.
Inline tasks are bullets in their parent's `## Subtasks` list with nowhere to
put a scalar. We chose to keep order in front matter unconditionally rather than
extend the subtask bullet grammar, which means:

- Assigning a non-default order to an inline task **auto-upgrades it to basic
  form** (a file is created), the same auto-upgrade pattern as `add --details`.
- `order --front <a> --rest` materializes a *total* order over every sibling from
  `a` onward, so one command can convert a whole story's inline subtask list into
  a directory of files.

Order values are an internal implementation detail: no CLI or MCP surface accepts
a raw order integer. Users only ever express *relative* placement (`tasker order`,
`--front`, `--clear`, MCP `order_tasks`). Values are sparse (stepped by 1000) with
midpoint insertion so ordering one task does not rewrite untouched neighbours;
values are re-spaced only when a gap runs out of room. Dense contiguity is a
write-time normalization, not a read-time invariant — the sort key is
`(order is None, order, id)`, which tolerates gaps and post-merge duplicates.

## Consequences

- Imposing an implementation order structurally changes the repo: inline tasks
  become files. This is visible in git as new files/directories, not a one-line
  edit.
- Clearing a task's order (`tasker order --clear`, or a plain `move`, which drops
  order) auto-downgrades it back to inline when it has no other reason to be a
  file — so the structural change is reversible per task.
- `resolve` treats `order` as an ordinary front-matter scalar; it needs no
  cross-file sibling logic because the sort tolerates gaps and duplicates.

## Considered Options

- **Store order for inline tasks in the `## Subtasks` bullet grammar** (front
  matter for file tasks, a token in the bullet for inline). Ordering would never
  force a file, keeping ordered and unordered tasks structurally uniform.
  Rejected: it extends the subtask bullet format users see and every parser that
  reads it (`parse`, `render`, `merge`, `resolve`), for a field that is otherwise
  a plain front-matter scalar. The chosen model keeps all four parsers untouched
  and accepts file materialization as the cost.
- **Scope `--rest` to the already-ordered set only** (rotate ordered tasks, leave
  the unordered tail alone) to avoid mass upgrades. Rejected: ordered and
  unordered tasks are indistinguishable to a user reading a listing, so a `--rest`
  that silently skips the "unordered" ones would behave unpredictably. A total
  order is the predictable behavior; the file churn is the honest cost.
