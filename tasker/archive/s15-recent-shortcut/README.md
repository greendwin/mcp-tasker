---
id: s15
status: done
---

# Recent shortcut

Support 'q' placeholder that references last created story or last parent in 'add' command.

Example:
```bash
tasker new "Story"  # s12 created, q := s12
tasker add q "Subtask 1"  # add to s12
tasker add q "Subtask 2"

tasker add q01 "Deep subtask 1"   # add to s12t01
tasker add q01 "Deep subtask 2"

tasker add s12t02 "Other subtask 1"  # q := s12t02
tasked add q "Other subtask 2"  # add to s12t02
tasker start q01  # started s12t0201
```

## Subtasks

- [x] ~~s15t01: Need git-ignored config aka `.tasker`~~
- [x] ~~s15t02: Need 'init' command that setups 'planning' directory~~
- [x] s15t03: TBD: we can add tasker directory instead of planning, put .gitignore there so that last task can be stored there
- [x] s15t04: Rework 'planning' to 'tasker'
- [x] [s15t05](s15t05-store-last-target-task.md): Store last target task
- [x] s15t06: Shortcuts usage should NEVER update 'recent'
- [x] [s15t07](s15t07-bug-on-add-new-tasks.md): BUG: on add new tasks overrides 'recent'
- [x] ~~s15t08: TBD: move to parent should target parent, not a new child~~
- [x] s15t09: Support 'pp' reference aka parent of the parent
