---
id: s19t20
slug: show-callstacks-only-when-debug
status: done
---

# Show callstacks only when --debug

Show callstacks only when --debug flag is set.

1. Wrap `read_text` and `write_text` in `utils.py` to catch `OSError` and re-raise as `TaskerError` with `file_path` attached.
2. In `catching_errors`, change the `except Exception` branch to suppress tracebacks without `--debug` (plain mode: red message + exit 1; JSON mode: `{error}` only). With `--debug`: full traceback in both modes. Consistent behavior for all exception types.
