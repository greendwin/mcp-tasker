---
id: s26t11
slug: renaming-task-title-during-add
status: done
---

# Renaming task title during 'add' shows previous title

## Bug

When `tasker add <parent> "Title" -e` opens the editor and the user changes the task title (or slug/description), the post-add output (parent preview) shows the **old** title. Data on disk is correct; only the display is wrong.

## Root cause

`edit_task_in_editor()` builds a fresh `TaskRepo` to re-read disk state and returns the updated `Task`, but the caller still holds the original (now-stale) `TaskRepo`. `print_parent_preview(repo, child)` walks via the stale repo, pulling cached child Task instances with their pre-edit titles. Same class of bug affects `cmd_new_task` and `cmd_edit_task`.

## Plan

- Add `TaskLoader.reload_root_tree(root_id)`:
  - Re-parse the root tree into a temporary `TaskLoader` (reusing `_load_task_tree`).
  - Merge into `self` **in-place, preserving Task identity**: for each ID, copy mutable fields (`title`, `description`, `status`, `slug`, `extended`, `extra_sections`, `archived`) onto the existing `Task`; reconcile `subtasks` list reusing existing instances by ID, inserting new ones for added inline subtasks, dropping removed ones.
  - Refresh `_original_state` for the tree.
- Add `TaskRepo.reload_root_tree(root_id)` thin wrapper.
- Rewrite `edit_task_in_editor`:
  - Drop the `TaskRepo(repo.root)` re-creation.
  - After `run_editor`, call `repo.reload_root_tree(root_id)` unconditionally, then `repo.flush_to_disk()`, then return `repo.resolve_ref(task.id)`.
- Held `Task` references in callers stay valid (same instances, fields refreshed), so `print_parent_preview` etc. show the new title/slug/etc.

## Tests (TDD)

1. CLI repro: `tasker add` with `-e` and a fake editor that rewrites the title; assert parent preview output contains the **new** title. (Red before fix.)
2. Loader unit: resolve a task, mutate its file on disk, call `reload_root_tree`; assert `id(task)` unchanged and fields refreshed.
3. Slug-change regression: editor changes slug; assert displayed task reflects new slug.
4. Inline-subtasks reconciliation: rewrite file to add/remove inline subtasks; assert `subtasks` list reconciled by ID with identity preserved for retained children.

## Done criteria

- All four tests pass.
- `uv run tox` is clean (including pre-existing issues).
- Status moved to `in-review` via `review_task`.
