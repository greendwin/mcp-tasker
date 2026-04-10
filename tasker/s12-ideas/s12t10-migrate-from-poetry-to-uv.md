---
id: s12t10
slug: migrate-from-poetry-to-uv
status: done
---

# Migrate from poetry to uv

Full migration from Poetry to uv, replacing every layer: build backend, lockfile, dev dependencies, venv/runner, tox integration, CI workflow, release workflow, and all docs/config referencing Poetry.

## Scope

Seven layers to migrate:
1. Build backend (`poetry.core.masonry.api` → `hatchling`)
2. Dependency management / lockfile (`poetry.lock` → `uv.lock`)
3. Dev dependencies (`[tool.poetry.group.dev.dependencies]` → `[dependency-groups]`)
4. Virtual environment / runner (`poetry run` → `uv run`)
5. tox integration (`tox` → `tox` + `tox-uv` plugin)
6. CI workflow (`.github/workflows/ci.yml`)
7. Release workflow (`.github/workflows/release.yml`)

## Decisions

### Build backend: hatchling
Swap `[build-system]` to `hatchling`. Replace `[[tool.poetry.packages]]` with:
```toml
[tool.hatch.build.targets.wheel]
packages = ["src/tasker"]
```
Preserves the distribution name `mcp-tasker` / import name `tasker` mismatch.

### Lockfile: commit `uv.lock`
Matches current practice of committing `poetry.lock`. Enables `uv sync --frozen` in CI. Delete `poetry.lock` in the same commit.

### Dev dependencies: PEP 735 `[dependency-groups]`
Use a `dev` group (tool-agnostic, installed by default by `uv sync`). Move `pytest`, `pytest-cov`, `tox`, `tox-uv`, `mypy`, `black`, `isort`, `flake8`, `pyfakefs` there verbatim. Add `tox-uv` as a new dep.

### tox: keep it, use `tox-uv`
`tox-uv` replaces tox's venv creation with uv (much faster). Single-command workflow (`uv run tox`) is preserved. Use `runner = uv-venv-lock-runner` + `with_dev = true` to install the `dev` group directly from `uv.lock` — drops the duplicated inline `deps =` blocks in `tox.ini`. Both `lint` and `test` envs will share the full dev dep set (fine, install is nearly free with uv).

### Python pin: `.python-version` = 3.12
Add a `.python-version` file pinned to 3.12 as the primary dev version. tox still runs the full 3.10–3.14 matrix in CI, so coverage isn't lost.

### CI workflow (`ci.yml`)
- Drop `actions/setup-python`.
- Use `astral-sh/setup-uv@v5` with `enable-cache: true` (unpinned uv version).
- `uv python install ${{ matrix.python-version }}` for the matrix version.
- `uv sync --group dev`.
- `uv run tox`.
- **Drop the `.tox` cache step** — `tox-uv` makes env rebuilds fast enough.
- Update cache key: use `uv.lock` instead of `pyproject.toml`.

### Release workflow (`release.yml`)
- Drop `actions/setup-python` and `pip install build`.
- Use `astral-sh/setup-uv@v5` + `uv build`.
- Keep `pypa/gh-action-pypi-publish` for the actual upload (preserves OIDC trusted publishing).

### CLAUDE.md
Direct swap: `poetry run tox` → `uv run tox`. No other changes.

### README.md
Three sections to update (end-user pipx/pip install section stays unchanged):
- "For development" block: `poetry install --with dev` → `uv sync --group dev`, drop the Poetry link.
- MCP `.mcp.json` example for running from a checkout: `"command": "uv"`, `"args": ["run", "tasker", "mcp"]`.
- Development section: `poetry run tox` → `uv run tox`, bare `black`/`isort` → `uv run black`/`uv run isort` for consistency.

### `.mcp.json` (project root)
Swap `"command": "poetry"` → `"command": "uv"`. Functionally important — this is the MCP config Claude Code uses in this project.

### `.gitignore`
Leave the Poetry comment block alone (part of the standard Python gitignore template, harmless).

### Task title in `s12-ideas/README.md`
Leave unchanged (historical record).

## Execution order (single atomic commit)

1. Update `pyproject.toml`: swap `[build-system]`, add `[tool.hatch.build.targets.wheel]`, add `[dependency-groups] dev`, drop all `[tool.poetry*]` tables, keep `requires-python = ">=3.10"`.
2. Run `uv sync --group dev` locally to generate `uv.lock`.
3. Delete `poetry.lock`.
4. Update `tox.ini`: set `runner = uv-venv-lock-runner` + `with_dev = true`, drop inline `deps =` blocks.
5. Add `.python-version` with contents `3.12`.
6. Verify locally: `uv run tox` green + `uv build` produces `dist/*.whl` and `dist/*.tar.gz`.
7. Update `.github/workflows/ci.yml` and `.github/workflows/release.yml`.
8. Update `.mcp.json`, `README.md`, `CLAUDE.md`.
9. Commit.

## Verification bar before commit

- `uv run tox` passes all envs.
- `uv build` produces a valid wheel and sdist without errors (the only local check for the hatchling build-backend swap; release workflow is otherwise the first place a broken backend would surface).

## Out of scope

- No subtask decomposition — migration is one atomic commit.
- No uv version pinning in CI (`[tool.uv] required-version` or action `version:`) — react if something breaks.
- No Makefile / shell wrapper — `uv run tox` stays the single entry point.
