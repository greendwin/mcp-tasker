---
id: s26t01
slug: bug-when-searching-for-tasker
status: done
---

# BUG: when searching for 'tasker' dir we should not pass '.git' directory -- it's clearly out of package

The issue is clear when we have following picture:

/work
| project/some/path <- run from here
| tasker <- nearby project with 'tasker' name

Possible solution: mark tasker dir somehow to make sure it's an inited directory, not an accidently same name. (e.g. check for .recent file -- in this case we need to make sure that it's created on `init`, another way is to add a comment to `.gitignore` in `tasker` dir)
