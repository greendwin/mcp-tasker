---
id: s19
slug: usability
status: pending
---

# Usability

Improve user experience

## Subtasks

- [x] s19t02: Omit markers in `view` command for pending tasks (show markers after ref same as in `list`)
- [x] ~~[s19t03](s19t03-rename-parent-to-attach.md): Rename `--parent` to `--attach` in `move` command~~
- [x] [s19t05](s19t05-support-autocomplete.md): Support autocomplete for task ids
- [x] [s19t06](s19t06-invoke-editor/): Invoke EDITOR in 'edit', e.g. t edit s19t06 -e|--editor
- [x] [s19t07](s19t07-editor-on-add.md): Support `--editor` option on task creation
- [x] s19t08: In 'list' command show task that is pointed by 'recent' label
- [x] s19t09: Unarchive root task when trying to 'edit' it
- [x] ~~s19t10: Always show recent task in 'list' command even if it filtered out by status~~
- [x] s19t11: Show (p) marker if (q) is hidden by filters, TBD: show (pp..) if (q) is deeper
- [x] [s19t12](s19t12-show-q-marker-in-view.md): Show (q) marker in 'view' and 'edit' commands
- [x] [s19t13](s19t13-show-subtasks-subtasks-count.md): Show subtasks subtasks count
- [x] [s19t14](s19t14-by-default-create-tasker-repo.md): Support user-level tasks in ~/.local/tasker
- [x] [s19t15](s19t15-support-e-option-for-move.md): Support -e option for 'move' command (i.e. edit after move)
- [x] [s19t16](s19t16-support-done-review-to-close.md): Support done --reviewed to close in-review tasks
- [x] [s19t17](s19t17-rework-lastclosed-to-clossed-flag.md): Rework implicit closed display to explicit `--closed` flag
- [x] ~~[s19t18](s19t18-support-inreview-state-for-nonleaf.md): Support 'in-review' state for non-leaf tasks~~
- [x] [s19t19](s19t19-group-renamed-tasks.md): Group renamed tasks
- [x] [s19t20](s19t20-show-callstacks-only-when-debug.md): Show callstacks only when --debug
- [x] [s19t21](s19t21-dont-show-finished-todo-tasks.md): Don't show finished tasks in 'list --todo' when active exists
- [ ] s19t22: 'tasker add XXX' should open editor with placeholders, same for 'tasker new'
- [x] [s19t23](s19t23-support-list-rev.md): Support `list --rev` / `--in-review`
- [x] [s19t24](s19t24-tasker-list-rev-must-show.md): Tasker list --rev must show --todo if nothing in review
- [ ] [s19t25](s19t25-install-shortcuts-to-bashrc-of.md): Install shortcuts to .bashrc of .zshrc/.zshuser
- [ ] [s19t26](s19t26-todo-list-must-be-commited.md): Todo list must be commited to git, don't ignore it
- [ ] s19t27: Support shortcuts s1, s02t2 - same as q1, ta2
