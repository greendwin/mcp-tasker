---
id: s26t05
slug: titles-and-description-any-user
status: done
---

# Titles and description (any user text) can contain [words] that are incorrectly printed by rich

Rich treats `[word]` sequences in strings as markup tags, so task titles, descriptions, and extra sections containing literal brackets (e.g. `Fix [auth] bug`) are mangled when printed. Error messages that embed a user-supplied ref have the same issue.

Fix: add an `escape_markup` helper in `utils.py` wrapping `rich.markup.escape`, and call it at the render boundary wherever user-provided text is spliced into a markup-enabled print:

- `format_task_list_item` (title)
- `print_task` (description, extra_sections)
- the `TaskerError` line in `OutputContext.catching_output`
