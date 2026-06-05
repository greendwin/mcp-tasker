---
id: s19t2904
slug: full-task-merge-with-conflict
status: done
---

# Full task merge with conflict markers

## Goal

Combine scalar merge + subtask merge to produce a complete merged task. Inject git conflict markers into prose fields (description, extra_sections) when both branches diverged. Recalculate non-leaf status.

## Decisions & constraints

- Non-leaf status recalculated via `get_status_from_subtasks`. Leaf status uses scalar merge.
- Standard `<<<<<<<`/`=======`/`>>>>>>>` markers for prose conflicts.
- Returns a structured result: merged content string + whether file has unresolved conflicts.
- Uses `render_task()` for serialization, but needs custom handling to inject conflict markers into description/extra_sections before rendering.

## Edge cases

- File absent in base (add/add — both branches created it)
- File absent in one branch (delete/modify)
- Non-leaf with subtask conflicts still gets recalculated status from the successfully-merged children
- Mixed: subtasks auto-resolve but description conflicts

## Key files

- `src/tasker/merge.py`, `src/tasker/render.py`, `src/tasker/repo/_utils.py`

## Acceptance criteria

- Fully resolvable task → clean rendered markdown, no markers, `has_conflicts=False`
- Description conflict → rendered with `<<<<<<<`/`=======`/`>>>>>>>` in description section, `has_conflicts=True`
- Non-leaf task → status derived from children regardless of base/ours/theirs status values
- File missing in one stage → handled gracefully (add or delete scenario)
