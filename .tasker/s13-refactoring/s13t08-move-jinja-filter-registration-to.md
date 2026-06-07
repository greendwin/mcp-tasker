---
id: s13t08
slug: move-jinja-filter-registration-to
status: pending
---

# Register Jinja filters at module level in render.py

**Latent bug / cleanup**: Jinja filters `checkbox` and `subtask_line` are registered inside `render_task()` on every call (lines 45-46) instead of once at module level after `_jinja` is created.

Currently not triggerable — `render_task()` is the only code path that uses the Jinja template, so the filters are always registered before rendering. However, any new code path that uses `_jinja` directly without going through `render_task()` would fail with "No filter named 'subtask_line' found".

**Fix**: Move both filter registrations to module level, right after the `_jinja` Environment is created (after line 21):

```python
_jinja.filters["checkbox"] = _to_checkbox
_jinja.filters["subtask_line"] = render_subtask_line
```

Then remove the duplicate registrations from `render_task()`.
