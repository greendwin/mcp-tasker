---
id: s26t08
slug: show-the-name-of-broken
status: pending
---

# Show the name of broken file/taskref when reporting that has bad format

When a task .md file is manually edited and becomes malformed, the error message doesn't indicate which file is broken.

Decisions:
- Add optional `file_path` field (`Path | None`) to `TaskValidateError`
- Populate it at call sites where the path is known
- Update `catching_errors` in `utils.py` to append the path to the error message
- Path should be relative to the tasker directory (works for both in-repo and `~/.local/share/tasker`)
