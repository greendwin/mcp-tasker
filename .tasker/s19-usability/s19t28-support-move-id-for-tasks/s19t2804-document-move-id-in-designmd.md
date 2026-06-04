---
id: s19t2804
slug: document-move-id-in-designmd
status: done
---

# Document move --id in DESIGN.md

## Goal

Document the `--id` usage form and its semantics/boundary in `DESIGN.md`.

## Decisions & constraints

- Add `tasker move <task-id> --id <new-id>` to the `move` usage block (match the existing style around the other `move` forms).
- Add a concise prose note: renames a task to any free, canonically-valid id (shorthand like `s1t5` accepted), re-homes under the parent implied by the id, recursively relabels descendants; primarily for resolving id collisions after a merge; operates only on a loadable repo (hard dup-id states — ambiguous root dirs, subtask dups — are fixed on disk first).
- No task IDs in the text (per project convention).

## Key files

- `DESIGN.md`

## Acceptance criteria

- `DESIGN.md` shows the `--id` usage line and a concise prose note covering re-home, shorthand, and the loadable-repo boundary.
