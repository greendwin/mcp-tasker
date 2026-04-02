# Tasker

[![tests](https://github.com/greendwin/tasker/actions/workflows/ci.yml/badge.svg)](https://github.com/greendwin/tasker/actions/workflows/ci.yml)

A simple file-based task tracker for git repositories. Tasks are stored as plain Markdown files inside a `tasker/` directory, tracked alongside your code with git.

## Installation

Install with [pipx](https://pipx.pypa.io/) (recommended — installs in an isolated environment):

```bash
pipx install tasker
```

Or with pip:

```bash
pip install tasker
```

For development (requires [Poetry](https://python-poetry.org/)):

```bash
git clone https://github.com/greendwin/tasker.git
cd tasker
poetry install --with dev
```

## Quick Start

```bash
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
tasker add <parent-id> <title>              # inline subtask
tasker add <parent-id> <title> --details "..."    # subtask with description
tasker add-many <parent-id>                 # add multiple subtasks interactively
```

### Update status

```bash
tasker start <task-id>...     # mark in-progress
tasker done <task-id>...      # mark done
tasker cancel <task-id>...    # cancel
tasker reset <task-id>...     # reset to pending

# Force-close a parent with open subtasks
tasker done <task-id> --force
```

### View tasks

```bash
tasker list                   # all open root tasks
tasker list -a                # include closed tasks
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
| `view_task` | View task details and subtasks |
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
