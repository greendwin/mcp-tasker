---
id: s15t05
status: done
---

# Store last target task

Remember task id on following operations:
- new
- add
- move
- edit
- unarchive

Note: remember when task is referenced by *direct* reference.

```bash
# q := s01t02
tasker edit s01t02 -d "test"
```

Accessing using `q` NEVER updates reference

TBD: should we update `q` on ANY direct reference usage?
why `tasker start s01t02` does not reset `q` to `s01t02`?
HOw to reference its parent in this case?

We can add other shortcuts like `p` is a parent of `q`?
So if we need a sibling, we can do this:

```bash
tasker start s01t02
tasker start p03            # s01t03
tasker add p "new task"
```

## Location

`tasker/.recent` file with raw task id

## Subtasks

- [x] s15t0501: On any command store targeted task to quick-access (aka 'q' variable)
- [x] s15t0502: In multiple tasks input - story the later one
- [x] s15t0503: Store recent to 'tasker/.recent' and add 'tasker/.gitignore' that excludes .recent file
- [x] s15t0504: When creating .gitignore from scratch - add itself to ignore
- [x] s15t0505: Resolve 'q' reference
- [x] s15t0506: Resolve 'p' reference
- [x] s15t0507: Resolve 'q01', 'q0102...' reference
- [x] s15t0508: Resolve 'p01', 'p0102...' reference
