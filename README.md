# Tasker

[![tests](https://github.com/greendwin/mcp-tasker/actions/workflows/ci.yml/badge.svg)](https://github.com/greendwin/mcp-tasker/actions/workflows/ci.yml)

A Markdown task tracker designed to live in git alongside your code. Tasks are plain Markdown files inside a `tasker/` directory, with hierarchical stories and subtasks, a CLI for humans, and an MCP server so AI agents can manage the same task list.

## Installation

Install with [pipx](https://pipx.pypa.io/) (recommended — installs in an isolated environment):

```bash
pipx install mcp-tasker
```

Or with pip:

```bash
pip install mcp-tasker
```

For development (requires [uv](https://docs.astral.sh/uv/getting-started/installation/)):

```bash
git clone https://github.com/greendwin/mcp-tasker.git
cd mcp-tasker
uv sync --group dev
```

## Quick Start

```bash
# Initialize tasker (or let it auto-detect from any subdirectory)
tasker init

# Or initialize a user-level tasker in your home data directory
tasker init --user

# Create a story
tasker new "Build authentication"

# Add subtasks
tasker add s01 "Design login flow"
tasker add s01 "Implement JWT tokens" --details "Use RS256 signing"

# Work on a task
tasker start s01t01

# View what's on your plate
tasker list

# Mark tasks done
tasker done s01t01

# Edit a task in your editor
tasker edit s01t02
```

Tasks are stored as Markdown in `tasker/` and committed with your code:

```
tasker/
  s01-build-authentication/
    README.md
    s01t01-design-login-flow.md
    s01t02-implement-jwt-tokens.md
```

## Usage

### Create tasks

```bash
tasker new <title>                          # new root story
tasker new <title> --details "..." --slug <slug>  # with description and slug
tasker new <title> --editor                 # create and open in editor
tasker add <parent-id> <title>              # inline subtask
tasker add <parent-id> <title> --details "..."    # subtask with description
tasker add <parent-id> <title> --editor     # create and open in editor
tasker add-many <parent-id>                 # add multiple subtasks interactively
```

### Update status

```bash
tasker start <task-id>...     # mark in-progress
tasker review <task-id>...    # submit leaf task for review
tasker done <task-id>...      # mark done
tasker cancel <task-id>...    # cancel
tasker reset <task-id>...     # reset to pending
tasker reset <task-id> --force  # force reset non-pending subtasks

# Force-close a parent with open subtasks
tasker done <task-id> --force

# Close every in-review task along with any explicitly listed ones
tasker done --reviewed
```

### View tasks

```bash
tasker list                   # all open root tasks
tasker list -a                # include closed tasks
tasker list --todo            # only tasks from the TODO list
tasker list --archived        # list archived tasks
tasker list --closed          # show 5 most recently closed tasks
tasker list <task-id>         # subtasks of a specific task
tasker view <task-id>         # full task details
```

### TODO list

Pin tasks you're actively focused on. The list lives in `tasker/.todo` (git-ignored), and archived tasks are removed automatically.

```bash
tasker todo <task-id>...      # pin task(s) to the TODO list
tasker untodo <task-id>...    # remove from the TODO list
tasker list --todo            # show only pinned tasks
```

### Edit tasks

```bash
tasker edit <task-id>                    # open in $EDITOR
tasker edit <task-id> --title "New title"
tasker edit <task-id> --details "New description"
tasker edit <task-id> --slug new-slug
```

### Organize

```bash
tasker move <task-id> --parent <new-parent>  # reparent
tasker move <task-id> --root                 # promote to story
tasker move <task-id> --delete               # delete a task
tasker move <task-id> --parent <p> --editor  # reparent and open in editor
tasker archive <task-id>                     # archive completed story
tasker archive --closed                      # archive all closed stories
tasker unarchive <task-id>                   # restore from archive
```

### Shortcuts

Reference recent tasks without typing full IDs:

| Shortcut | Meaning |
|---|---|
| `q` | Last referenced task |
| `q01` | Subtask 01 of recent |
| `p` | Parent of recent |
| `p03` | Sibling 03 via parent |

```bash
tasker view s01t02   # sets recent = s01t02
tasker start q       # starts s01t02
tasker view p        # views s01 (parent)
tasker done q01      # marks s01t0201 done
```

## MCP Server

`tasker` can run as a [Model Context Protocol](https://modelcontextprotocol.io/) server, allowing AI agents to manage your tasks directly.

### Configure in Claude Code

```bash
claude mcp add tasker -- tasker mcp
```

### Configure per-project (`.mcp.json`)

```json
{
  "mcpServers": {
    "tasker": {
      "command": "tasker",
      "args": ["mcp"]
    }
  }
}
```

If running from a checkout:

```json
{
  "mcpServers": {
    "tasker": {
      "command": "uv",
      "args": ["run", "tasker", "mcp"]
    }
  }
}
```

### HTTP transport

For network-accessible clients, start with `--port`:

```bash
tasker mcp --port 8080
```

### Available tools

Once connected, the MCP server exposes:

| Tool | Description |
|---|---|
| `create_task` | Create a root task or subtask |
| `list_tasks` | List all root tasks (pass `todo=true` for only pinned tasks) |
| `view_tasks` | View detailed info for multiple tasks |
| `edit_task` | Update a task's title, description, or slug |
| `start_task` | Mark task in-progress |
| `review_task` | Mark task in-review (submit for review) |
| `reset_task` | Reset task to pending |
| `finish_task` | Mark task done |
| `cancel_task` | Cancel a task |

## Development

```bash
uv sync --group dev

# Run all checks (lint + tests)
uv run tox

# Run tests only
uv run tox -e test

# Lint (black, isort, flake8, mypy)
uv run tox -e lint

# Format code
uv run black src tests
uv run isort src tests
```

## Requirements

- Python >= 3.10

## Release Notes

### 1.3.4
- Warning shown when a task directory is missing its `README.md`
- Exception callstacks hidden by default, shown only with `--debug`
- Renamed tasks displayed as a single group in `move` output
- Bug fixes: broken task files now report the offending filename in the error message

### 1.3.3
- Task preview after `done`/`cancel` walks up to the first non-closed ancestor, showing the full picture of remaining work
- When closing a task completes the entire story, nearby open stories are shown as a "what's next?" hint

### 1.3.2
- Bug fixes: proper error handling for exceptions raised in dependency-injection callbacks (e.g. missing `tasker/` directory)

### 1.3.1
- `list --closed` flag to explicitly show recently closed tasks (previously shown implicitly at the end of `list`)
- Bug fixes: `list --todo` no longer shows non-TODO tasks

### 1.3.0
- `in-review` status and `tasker review` command for submitting leaf tasks
- `done --reviewed` closes every currently in-review task in one call
- `todo` / `untodo` commands to pin tasks, and `list --todo` / `(todo)` marker
- Archived tasks are auto-removed from the TODO list
- `init --user` creates a user-level tasker directory (respects `XDG_DATA_HOME` / `LOCALAPPDATA`)
- `move --editor` to open the moved task after reparenting
- `new` and `add` accept unquoted titles (extra words are joined automatically)
- Recently closed tasks are shown at the end of `list` output
- Last two digits of subtask IDs are highlighted in bullet lists
- MCP: added `cancel_task` tool, `todo` parameter on `list_tasks`
- MCP: status tools return smaller previews on `start` / `cancel` / `review` / `done`
- Build: migrated from `poetry` to `uv`
- Bug fixes: `[text]` escaping in task output, stale `(q)` reference to deleted tasks, `tasker` directory resolution, recently closed task suppressed on narrow terminals

### 1.2.0
- `init` command and automatic `tasker/` directory discovery (walks up to git root)
- `move --delete` option to delete tasks
- `reset --force` to force-reset non-pending subtasks
- `(q)` / `(p)` recent-task markers shown in `view` and `edit` commands
- Subtask count shown in `view` command
- Tab autocompletion for task ID arguments
- Slug validation
- Bug fixes: recent task override, auto-unarchive logic

### 1.1.0
- `--editor` (`-e`) option on `new` and `add` commands to open the task in an editor after creation
- `list --archived` to browse archived tasks
- `list` highlights the most recently referenced task
- Editing an archived task auto-unarchives it
- Task preview shown after `start`, `reset`, `done`, `cancel`, `move`, `new`, `add`, and `edit` commands
- MCP: added `edit_task` tool for updating title, description, and slug
- MCP: `view_tasks` accepts multiple task IDs in a single call
- MCP: task subtasks grouped by status in response
- `--version` flag
- Bug fixes: editor slug path, directory cleanup on `move`, multi-task preview on `start`

### 1.0.0
- `pip` release