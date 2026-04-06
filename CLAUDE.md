# Project

`tasker` is a simple file-based task tracker for git repositories. CLI built with `typer`, src layout under `src/tasker/`.

Detailed design is described in `DESIGN.md`.

## Development

* On any development iteration, the final step is to run `poetry run tox` (all environments).
* Always fix **all** reported `tox` issues including **pre-existing**.
* Never use `type: ignore` if it can be fixed normally.
* Never include ticket IDs into code comments.
* Never use `unittest.mock.patch`, use `monkeypatch`.