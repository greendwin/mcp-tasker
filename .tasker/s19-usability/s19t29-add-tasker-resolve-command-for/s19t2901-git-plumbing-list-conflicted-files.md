---
id: s19t2901
slug: git-plumbing-list-conflicted-files
status: done
---

# Git plumbing: list conflicted files and extract index stages

## Goal

A `git.py` module that can list unmerged files under `.tasker/` and retrieve the base/ours/theirs content for each from git's index.

## Decisions & constraints

- Per-file extraction from git index stages (`:1:`, `:2:`, `:3:`). Only process `git ls-files --unmerged`. Works for merge, rebase, cherry-pick.
- First use of `subprocess` for git commands (outside editor launching). Must handle missing stages (e.g., delete-vs-modify where stage 1 or 2/3 may be absent).

## Edge cases

- File exists in only some stages (add/add, delete/modify)
- Binary files or non-markdown files under `.tasker/` (`.gitignore`, `.gitkeep`)

## Key files

- `src/tasker/git.py` (new)

## Acceptance criteria

- Given unmerged entries in git index, returns list of conflicted paths under a given directory
- For each path, retrieves content strings for base/ours/theirs (None when stage missing)
- Can stage a resolved file via `git add`
- Returns empty list when no conflicts exist
