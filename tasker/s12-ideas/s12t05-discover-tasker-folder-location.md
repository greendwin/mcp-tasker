---
id: s12t05
slug: discover-tasker-folder-location
status: done
---

# Discover 'tasker' folder location

When invoked outside of project root - we must correctly located tasker dir -- search parent directories upward, or create it near .git directory

1. Search current and parent directories for existing `tasker` folder
2. Search for `.git` folder and auto-init tasker there
3. Report that `tasker init` should be invoked if you want to use it outside of git repo

Add `init` method, that initialize current directory:
* Create `tasker` folder
* Add `.gitignore` with excluded `.recent`
* Don't need auto-gitignore creation in recent methods -- `init` or `auto-init` should handle this
