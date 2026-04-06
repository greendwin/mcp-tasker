# Tasker

[![tests](https://github.com/greendwin/mcp-tasker/actions/workflows/ci.yml/badge.svg)](https://github.com/greendwin/mcp-tasker/actions/workflows/ci.yml)

A simple file-based task tracker for git repositories. Tasks are stored as plain Markdown files inside a `tasker/` directory, tracked alongside your code with git.

## Installation

Install with [pipx](https://pipx.pypa.io/) (recommended — installs in an isolated environment):

```bash
pipx install mcp-tasker
```

Or with pip:

```bash
pip install mcp-tasker
```

For development (requires [Poetry](https://python-poetry.org/)):

```bash
git clone https://github.com/greendwin/mcp-tasker.git
cd mcp-tasker
poetry install --with dev
```

## Quick Start

```bash
# Initialize tasker (or let it auto-detect from any subdirectory)
tasker init

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
tasker done <task-id>...      # mark done
tasker cancel <task-id>...    # cancel
tasker reset <task-id>...     # reset to pending
tasker reset <task-id> --force  # force reset non-pending subtasks

# Force-close a parent with open subtasks
tasker done <task-id> --force
```

### View tasks

```bash
tasker list                   # all open root tasks
tasker list -a                # include closed tasks
tasker list --archived        # list archived tasks
tasker list <task-id>         # subtasks of a specific task
tasker view <task-id>         # full task details
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

If running from a Poetry project:

```json
{
  "mcpServers": {
    "tasker": {
      "command": "poetry",
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
| `list_tasks` | List all root tasks |
| `view_tasks` | View detailed info for multiple tasks |
| `edit_task` | Update a task's title, description, or slug |
| `start_task` | Mark task in-progress |
| `reset_task` | Reset task to pending |
| `finish_task` | Mark task done |

## Development

```bash
poetry install --with dev

# Run all checks (lint + tests)
poetry run tox

# Run tests only
poetry run tox -e test

# Lint (black, isort, flake8, mypy)
poetry run tox -e lint

# Format code
black src tests
isort src tests
```

## Requirements

- Python >= 3.10

## Release Notes

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