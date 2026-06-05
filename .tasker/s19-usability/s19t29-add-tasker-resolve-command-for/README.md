---
id: s19t29
slug: add-tasker-resolve-command-for
status: done
---

# Add `tasker resolve` command for merge conflicts in .tasker dir

## Context

The `.tasker/` directory is tracked in git, and when branches diverge, git's line-based merge produces conflicts in task files — especially in `## Subtasks` bullet lists where both branches added/changed tasks. We need a `tasker resolve` command that performs semantic three-way merging at the task-model level, auto-resolving what it can and leaving standard conflict markers for the rest.

## Decisions

- **Per-file three-way merge from git index stages** — extract base/ours/theirs via `git show :1:/:2:/:3:` for each conflicted file, parse each into Task structures using existing `parse_task()`. *Rejected: directory-level snapshot into temp dirs (heavier, no benefit).*
- **Semantic merge for subtask lists, opaque blobs for prose** — subtask bullets are merged per-task-ID (adds, removes, status/title changes). Description, title, and extra sections are compared as opaque blobs. *Rejected: line-level diffing of prose.*
- **Conservative conflict policy** — auto-resolve uncontested changes (one-sided adds, removes, status changes, renames). Flag as conflict when both branches modified the same task ID differently or the same prose section differently.
- **Non-leaf status is always recalculated** — derived from merged subtasks via existing `get_status_from_subtasks()`, never a true conflict. Leaf status with both-sides-changed is a conflict.
- **Sorted by task ID after merge** — final subtask order is sorted by ID. *Rejected: three-way list merge preserving relative order (complex, IDs encode natural order).*
- **Standard git conflict markers for unresolved parts** — `<<<<<<<`/`=======`/`>>>>>>>` for description/title/extra sections where both branches diverged. *Rejected: custom tasker markers (no tooling support).*
- **Fully resolved files are `git add`ed; partial files are not** — user finishes partial files with normal merge tools.
- **Only process git-reported conflicts** — `git ls-files --unmerged` under `.tasker/`. Works for merge, rebase, and cherry-pick.
- **Ignore conflicts outside `.tasker/`** — mentions remaining non-tasker conflicts in summary.
- **No arguments, no dry-run** — processes all conflicted `.tasker/` files.
- **Rich-colored CLI output** — per-file status (green resolved, yellow conflicts), colored summary.
- **Module structure** — `src/tasker/merge.py` (pure three-way logic), `src/tasker/git.py` (index plumbing), CLI command in `src/tasker/cli/`.

## Out of scope

- Custom git merge driver (`.gitattributes` integration)
- Interactive conflict resolution UI
- `--dry-run` flag
- Archived tasks merging (separate task)

## Subtasks

- [x] [s19t2901](s19t2901-git-plumbing-list-conflicted-files.md): Git plumbing: list conflicted files and extract index stages
- [x] [s19t2902](s19t2902-threeway-scalar-merge-primitive.md): Three-way scalar merge primitive
- [x] [s19t2903](s19t2903-subtask-list-merge.md): Subtask list merge
- [x] [s19t2904](s19t2904-full-task-merge-with-conflict.md): Full task merge with conflict markers
- [x] [s19t2905](s19t2905-cli-command-and-endtoend-integration.md): CLI command and end-to-end integration
- [x] [s19t2906](s19t2906-defensive-parsing-for-malformed-git.md): Defensive parsing for malformed git ls-files output
- [x] [s19t2907](s19t2907-handle-pureposixpath-directory-normalization-for.md): Handle PurePosixPath directory normalization for Windows compatibility
