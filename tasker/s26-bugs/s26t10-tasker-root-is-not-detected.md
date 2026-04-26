---
id: s26t10
slug: tasker-root-is-not-detected
status: cancelled
---

# Tasker root is not detected on fresh git clone (legacy setups)

Affects **old tasker setups** that predate the `# tasker` header in `tasker/.gitignore`.
On fresh clone such repos have neither the `.recent` marker (git-ignored) nor a
gitignore with the header, so `is_tasker_dir` returns False and `discover_tasker_dir`
fails with `TaskerNotFoundError`.

Newly initialized repos (`tasker init`) are fine: `init_tasker_dir` writes
`tasker/.gitignore` containing the `# tasker` header and ignores only `.recent`,
`.todo`, `.closed` — the gitignore itself is not in its own ignore list, so it is
committed and visible to other clones, and detection works via the header check.

## Fix options

- Detect a tasker dir by the presence of root-level story files (e.g. `sNN-*.md`
  / `sNN-*/`) or an `archive/` directory, in addition to the `.gitignore` header
  and `.recent` marker.
- Or document a one-time migration: run `tasker init` again in legacy repos to
  upgrade `tasker/.gitignore` with the header and commit it.
