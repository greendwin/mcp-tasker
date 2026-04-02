# Tasker

[![tests](https://github.com/greendwin/tasker/actions/workflows/ci.yml/badge.svg)](https://github.com/greendwin/tasker/actions/workflows/ci.yml)

A simple file-based task tracker for git repositories.

## Installation

```bash
pip install tasker
```

Or with Poetry:

```bash
poetry install
```

## Usage

```bash
tasker hello
tasker hello Alice
```

## MCP Server

`tasker` can run as a [Model Context Protocol](https://modelcontextprotocol.io/) server over stdio, allowing AI agents to interact with your tasks directly.

### Configure in Claude Code

```bash
claude mcp add tasker -- tasker mcp
```

### Configure in project scope

Configure per-project via `.mcp.json`:

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

## Development

```bash
poetry install --with dev

# Run tests
pytest tests/ -v

# Lint + type check
tox -e lint

# Format
black src tests
isort src tests
```

## Requirements

- Python >= 3.10
