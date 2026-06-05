---
id: s19t2903
slug: subtask-list-merge
status: done
---

# Subtask list merge

## Goal

Given three lists of parsed subtasks (base, ours, theirs), produce a merged list sorted by task ID plus a list of per-subtask conflicts.

## Decisions & constraints

- Per-task-ID three-way merge. Adds from one side kept. Removes from one side accepted (unless other side modified — conflict). Uncontested status/title changes taken. Both-sides-changed same ID → conflict.
- Result sorted by task ID.
- Uses scalar merge primitive from s19t2902 for per-field comparison within each subtask.

## Edge cases

- Both branches add different tasks with different IDs (no conflict, both kept)
- Both branches add same task ID with different titles
- One branch removes a task, the other changed its status
- Task present in base, unchanged in both (passthrough)

## Key files

- `src/tasker/merge.py`

## Acceptance criteria

- Base `[t01, t02]`, ours adds `t03`, theirs adds `t04` → `[t01, t02, t03, t04]`
- Base `[t01, t02]`, ours removes `t02`, theirs unchanged → `[t01]`
- Base `[t01]` pending, ours marks done, theirs unchanged → `[t01]` done
- Base `[t01]`, ours changes title, theirs changes status → both changes merged
- Both change `t01` title differently → conflict on `t01`
