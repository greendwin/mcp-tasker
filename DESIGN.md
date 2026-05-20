DESIGN
======

File-based task structure and CLI command reference for `tasker`.

---

## Task Model

Everything is a **task**. Tasks are recursive — any task can have subtasks at any depth.

- A **story** (`s01`) is a root-level task. Story numbers are unlimited (`s01`, `s02`, … `s123`).
- **Subtasks** extend the parent ID by appending two digits after `t`. Each level adds exactly two digits, giving a limit of 99 siblings per parent.

### Task Forms

| Form | Structure | When to use |
|---|---|---|
| Inline | ID + title in parent's `## Subtasks` bullet list | Leaf task, no description needed |
| Basic | `sNN-short-name.md` | Task needing description or inline subtasks |
| Extended | `sNN-short-name/README.md` + child files … | Subtasks that each need their own file |

All tasks have an ID regardless of form. A slug (and therefore a filename) is only needed when a task has its own file (basic or extended form).

Tasks **auto-upgrade** when structure requires it:
- Promoting an inline task to have a description → basic form (file created)
- Adding a subtask with `--details` to a basic task → extended form (dir is created, existing file becomes `README.md`)

Tasks **auto-downgrade** when structure allows it (triggered during `move`):
- Extended task with no file-based subtasks remaining → basic form (dir collapsed to single file)
- File-based non-root task with no description, no extra sections, and no subtasks → inline form (file removed, becomes a bullet in parent)

---

## Task ID Scheme

Stories use an `s` prefix followed by a zero-padded number (no upper limit):

```
s01   s02   s03   …   s123   …
```

Subtasks extend the parent ID with `t` (first level only) and then append two digits per nesting level:

```
s01t01          ← task 01 inside story s01
s01t0102        ← subtask 02 inside task s01t01
s01t010203      ← sub-subtask 03 inside task s01t0102
```

Rules:
- The `t` separator appears once, immediately after the story number.
- Every nesting level after that adds exactly **two digits** (01–99).
- Maximum 99 siblings at any level below a story.

---

## Filename Format

Files with their own file (basic or extended) include a short summary slug appended to the ID:

```
s01-design-file-structure.md
s01-design-file-structure/        ← extended form (dir)
  README.md
  s01t01-define-task-forms.md
  s01t01-define-task-forms/       ← nested extended form
    README.md
    s01t0101-first-subtask.md
    s01t0102-second-subtask.md
  s01t02-write-cli-spec.md
```

**Rules:**
- Slug is only required for basic and extended tasks (those with their own file)
- Inline tasks have an ID but no slug and no file
- Slug is kebab-cased, max 5 words
- Derived automatically from the task title, or set explicitly via `--slug`
- The slug is cosmetic — tasks are always addressed by ID alone (`s01`, `s01t02`, `s01t0102`)
- When referencing a task in commands, both forms are accepted:
  - `s01t01` — ID only
  - `s01t01-define-task-forms` — full filename stem (slug ignored for lookup)

---

## File Structure

### Basic task

```
tasker/
  s01-design-file-structure.md
```

### Basic task with inline subtasks

```
tasker/
  s01-design-file-structure.md    ← contains ## Subtasks bullet list
```

### Extended task (recursive)

```
tasker/
  s01-design-file-structure/
    README.md                     ← task description + list of subtask links
    s01t01-define-task-forms.md   ← basic subtask
    s01t02-write-cli-spec/        ← extended subtask
      README.md
      s01t0201-draft-commands.md
      s01t0202-write-tests.md
```

Root-level stories live directly under `tasker/`. Archived tasks move to `tasker/archive/`.

---

## Task File Format

```
---
id: s01t02
slug: write-cli-spec
status: pending
---

# Title

Optional description text.
Can span multiple paragraphs.

## Subtasks

- [ ] s01t01: pending subtask
- [~] s01t02: in-progress subtask
- [x] s01t03: finished subtask
- [x] ~~s01t04: cancelled subtask~~
```

**Front matter** (YAML block between `---` delimiters):

| Field | Required | Description |
|---|---|---|
| `id` | yes | Task ID (e.g. `s01`, `s01t02`) |
| `status` | yes | One of `pending`, `in-progress`, `in-review`, `done`, `cancelled` |
| `slug` | no | Filename slug (present in basic/extended tasks, absent for inline) |

| Status value | Meaning |
|---|---|
| `pending` | not started |
| `in-progress` | being worked on |
| `in-review` | submitted for review |
| `done` | finished |
| `cancelled` | cancelled |

**`## Subtasks`** — present in the basic form when it has inline subtasks. Each line is a checkbox entry with the subtask ID and title.

For the **extended** form, `README.md` lists subtasks as links:

```
---
id: s01
status: in-progress
---

# Title

## Subtasks

- [ ] [s01t01](s01t01-define-task-forms.md): Define task forms
- [~] [s01t02](s01t02-write-cli-spec/): Write CLI spec
- [x] [s01t03](s01t03-finished-task.md): Finished task
- [x] ~~[s01t04](s01t04-cancelled-task.md): Cancelled task~~
```

---

## Checkbox Symbols

| Symbol | Status |
|---|---|
| `- [ ]` | pending |
| `- [~]` | in-progress |
| `- [~] …: **review** Title` | in-review (bold tag before title) |
| `- [x]` | done |
| `- [x] ~~…~~` | cancelled (strikethrough whole entry) |

---

## CLI Commands

All commands support `--json-output` for machine-readable output, `--debug` for full tracebacks, and `--version` for version info. Task ID arguments support tab autocompletion.

### Initialize

```bash
# Initialize tasker in the current directory (creates .tasker/ and archive/)
tasker init

# Initialize user-level tasker (~/.local/share/tasker on Linux/macOS, %LOCALAPPDATA%\tasker on Windows)
tasker init --user
```

`tasker init` creates `.tasker/`; if a legacy `tasker/` already exists at the project root it's kept as-is (no parallel `.tasker/`). The user-level dir stays `tasker/`.

Discovery walks up from the current directory, preferring `.tasker/` over legacy `tasker/` at each level, then falls back to the user-level dir. Respects `XDG_DATA_HOME` on Linux/macOS and `LOCALAPPDATA` on Windows.

### Add tasks

Title can be passed as a single quoted string or as separate words (quotes are optional):

```bash
# Add a root-level story (slug auto-derived from title)
tasker new <title>
tasker new <title> <extra-words...>

# Add a root-level story with explicit slug and description
tasker new <title> --slug <slug> --details <description>

# Create as a directory from the start
tasker new <title> --extended

# Create and open in editor for manual adjustments
tasker new <title> --editor
tasker new <title> -e

# Add a simple inline subtask under any parent
tasker add <parent-id> <title>
tasker add <parent-id> <title> <extra-words...>

# Add a subtask with details — auto-upgrades parent to extended form
tasker add <parent-id> <title> --details <description>

# Add with explicit slug (e.g. when created by AI)
tasker add <parent-id> <title> --details <description> --slug <slug>

# Add and open in editor for manual adjustments
tasker add <parent-id> <title> --editor
tasker add <parent-id> <title> -e

# Add multiple inline subtasks interactively (empty line or EOF ends input)
# In --json-output mode: reads stdin silently, emits { "parent_ref": "s01", "task_refs": ["s01t01", ...] }
tasker add-many <parent-id>
```

### Update task status

Status commands accept one or more task IDs. Parent tasks with subtasks have their status managed automatically — use `--force` to override.

```bash
# Mark in-progress
tasker start <task-id>...

# Mark in-review (leaf tasks only)
tasker review <task-id>...

# Mark done (fails if task has open subtasks)
tasker done <task-id>...

# Force close even with open subtasks
tasker done <task-id> --force

# Close every currently in-review task in one call (combines with explicit IDs)
tasker done --reviewed
tasker done --rev

# Cancel a task
tasker cancel <task-id>...

# Force cancel all open subtasks
tasker cancel <task-id> --force

# Reset a task back to pending
tasker reset <task-id>...

# Force reset all non-pending subtasks
tasker reset <task-id> --force
```

### View tasks

The `list` and `view` commands show markers for the most recently referenced task: `(q)` if the recent task is visible, or `(p)` / `(pp)` pointing to the nearest visible ancestor.

```bash
# View full task details and subtasks
tasker view <task-id>

# List all open root tasks with their pending subtasks
tasker list

# List subtasks of specific task(s)
tasker list <task-id>...

# Show all subtasks including closed (done/cancelled)
tasker list --all
tasker list -a

# List archived tasks
tasker list --archived
tasker list --arch

# Show only tasks pinned to the TODO list
tasker list --todo

# Show tasks awaiting review. When none are in review, falls back to the
# TODO list if it has any active pinned tasks; otherwise to active roots.
tasker list --in-review
tasker list --rev

# Show up to 5 most recently closed tasks
# (mutually exclusive with --archived, --todo, --in-review, and positional task refs)
tasker list --closed
```

Closed-task history is tracked in `tasker/.closed` (git-ignored) as a plain-text list of task IDs, newest last. The file grows as `done` / `cancel` append the user-specified refs (forced-closed children are not appended), is capped at 30 entries, and deduplicates on re-close so a reopened-and-closed task moves to the newest position. Stale IDs (deleted tasks) are pruned lazily whenever `list --closed` reads the file; `list --closed` keeps reading deeper into the history to surface 5 live tasks even if some entries have become stale.

### TODO list

Pin tasks you're actively working on so they are easy to retrieve. The list is stored in `tasker/.todo` (git-ignored) and auto-populated / pruned on archive operations.

```bash
# Pin one or more tasks to the TODO list
tasker todo <task-id>...

# Remove tasks from the TODO list
tasker untodo <task-id>...

# Show only pinned tasks (combine with --all to include closed)
tasker list --todo
```

Pinned tasks are marked with `(todo)` in `list` output, or `(tX)` for the first 26 active todo tasks (where `X` is `a`..`z`); see [Recent task shortcuts](#recent-task-shortcuts). The list is stored in insertion order. `list --todo` hides finished pinned tasks while any active ones remain, and prints `All tasks finished!` when every pinned task is closed. Archiving a story auto-removes it (and its descendants) from the TODO list.

### Edit tasks

Editing an archived task automatically unarchives it first.

```bash
# Change title
tasker edit <task-id> --title <new-title>

# Change or add description (auto-upgrades inline task to file-based)
tasker edit <task-id> --details <new-description>

# Change slug
tasker edit <task-id> --slug <new-slug>

# Open task file in $VISUAL/$EDITOR (falls back to vi / notepad)
tasker edit <task-id> --editor
tasker edit <task-id> -e

# With no options: opens editor by default
tasker edit <task-id>
```

### Move tasks

```bash
# Move a task under a different parent
tasker move <task-id> --parent <new-parent-id>

# Promote a subtask to a root-level story
tasker move <task-id> --root

# Delete a task
tasker move <task-id> --delete

# Move and open in editor for manual adjustments
tasker move <task-id> --parent <new-parent-id> --editor
tasker move <task-id> --root -e
```

Moving re-generates task IDs to match the new location and prints the rename mapping. Source parents are auto-downgraded when possible.

### Archive

```bash
# Move root story to tasker/archive/
tasker archive <task-id>...    # alias: arch

# Cancel open subtasks before archiving
tasker archive <task-id> --force

# Archive all closed (done/cancelled) root stories
tasker archive --closed

# Restore an archived story
tasker unarchive <task-id>...  # alias: unarch
```

Only root stories can be archived. Archiving a non-root task is an error.

### Recent task shortcuts

The last referenced task is saved to `tasker/.recent` (git-ignored). Shortcuts:

| Shortcut | Resolves to | Example |
|---|---|---|
| `q` | Last referenced task | If recent is `s01t02`, `q` → `s01t02` |
| `qNN...` | Descendant of recent | `q0103` → `s01t020103` |
| `p` | Parent of recent task | If recent is `s01t02`, `p` → `s01` |
| `pNN...` | Sibling via parent | `p03` → `s01t03` |
| `pp` | Grandparent of recent | If recent is `s01t0102`, `pp` → `s01` |
| `ppNN...` | Uncle via grandparent | `pp0202` → `s01t0202` |
| `t<letter>` | Active TODO task by letter marker | `ta` → first active todo task |
| `t<letter>NN...` | Descendant of TODO task | `ta01` → first child of `ta` target |

A single trailing digit is padded to two (e.g. `q3` → `q03`, `ta3` → `ta03`); odd-length digit runs longer than one are rejected as ambiguous.

These shortcuts work in place of any `<task-id>` argument, including in MCP `task_ref` parameters.

---

## Examples

```bash
# Create a root story
tasker new "Design file structure"
# → tasker/s01-design-file-structure.md  (Status: pending)

# Create with description
tasker new "Design file structure" --details "Define how tasks are stored on disk"
# → tasker/s01-design-file-structure.md  (description included)

# Add an inline subtask (no file created, gets an ID in ## Subtasks list)
tasker add s01 "Define task forms"
# → - [ ] s01t01: Define task forms  (in tasker/s01-design-file-structure.md ## Subtasks)

# Add multiple inline subtasks in one session (empty line ends input)
tasker add-many s01
#   Adding tasks to s01 (empty line to finish):
#   > Define task forms
#   task s01t01 added
#   > Write CLI spec
#   task s01t02 added
#   >
#   Done: 2 task(s) added to s01.

# Add a subtask with details — auto-upgrades parent to extended form
tasker add s01 "Write CLI spec" --details "Cover all commands and options"
# → tasker/s01-design-file-structure/README.md  (parent upgraded)
# → tasker/s01-design-file-structure/s01t02-write-cli-spec.md

# Add a subtask under a subtask — two digits appended
tasker add s01t02 "Draft commands" --details "List every command with args"
# → tasker/s01-design-file-structure/s01t02-write-cli-spec/README.md  (parent upgraded)
# → tasker/s01-design-file-structure/s01t02-write-cli-spec/s01t0201-draft-commands.md

# AI-created task with explicit slug
tasker add s01 "Implement command parsing" --details "..." --slug "impl-cmd-parsing"
# → tasker/s01-design-file-structure/s01t03-impl-cmd-parsing.md

# Reference by ID or full name — both work
tasker start s01t02
tasker start s01t02-write-cli-spec

# Close workflow
tasker done s01t0201
tasker done s01t02
# Error: s01t02 has open subtasks. Use --force to override.

tasker done s01t01
tasker done s01

# Cancel a task
tasker cancel s01t01
# → s01t01 cancelled (rendered as strikethrough in subtask list)

# Force cancel a parent with open subtasks
tasker cancel s01 --force
# → all open subtasks cancelled, parent cancelled

# Reset a task back to pending
tasker reset s01t01
# → s01t01 reset to pending (strikethrough removed if was cancelled)
```

---

## MCP Server

`tasker mcp` starts a [Model Context Protocol](https://modelcontextprotocol.io/) server, allowing AI agents to manage tasks programmatically.

### Transport

```bash
# stdio (default) — used by Claude Code, Cursor, etc.
tasker mcp

# HTTP/SSE — for network-accessible clients
tasker mcp --port 8080
```

### Tools

| Tool | Parameters | Description |
|---|---|---|
| `create_task` | `title`, `parent?`, `description?` | Create a root task or subtask |
| `list_tasks` | `todo?` | List all root tasks (`todo=true` returns only pinned tasks) |
| `view_tasks` | `task_refs` | View tasks by IDs: title, status, description, and subtask IDs |
| `edit_task` | `task_ref`, `title?`, `description?`, `slug?` | Update a task's title, description, or slug |
| `start_task` | `task_ref` | Mark task in-progress |
| `review_task` | `task_ref` | Mark task in-review (submit for review) |
| `reset_task` | `task_ref`, `force?` | Reset task to pending (`force` resets non-pending subtasks) |
| `finish_task` | `task_ref`, `force?` | Mark task done (`force` closes open subtasks) |
| `cancel_task` | `task_ref`, `force?` | Cancel a task (`force` cancels open subtasks) |

### Resources

| URI | Description |
|---|---|
| `task://index` | All root tasks (same as `list_tasks`) |
| `task://{ref}` | Single task by ID (same as `view_tasks`) |
