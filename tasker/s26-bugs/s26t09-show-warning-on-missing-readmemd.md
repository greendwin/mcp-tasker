---
id: s26t09
slug: show-warning-on-missing-readmemd
status: pending
---

# Show warning on missing README.md in a directory

Show warning on missing README.md in a task directory.

When the task loader finds a directory and assumes README.md exists inside, but it's missing (e.g. after manual edits):
- In `_task_loader.py` at both root-task loading (~line 210) and subtask loading (~line 271), catch `FileNotFoundError` from `read_text`.
- Print `[yellow]Warning:[/yellow] Missing file '<filepath>', skipping` via `console.print`.
- In JSON mode, skip silently (task won't appear in output).
- Do NOT raise — continue loading remaining tasks.
