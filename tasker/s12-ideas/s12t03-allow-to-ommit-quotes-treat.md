---
id: s12t03
slug: allow-to-ommit-quotes-treat
status: done
---

# Allow to ommit quotes (treat extra arguments as words in created tasks)

Add `extra_words` positional argument (metavar="WORDS") to `new` and `add` commands so users can omit quotes around multi-word titles.

## Design decisions

- Scope: `new` and `add` commands only
- Add `extra_words: list[str]` positional arg alongside existing `title: str`
- Join logic inlined in each command: `title + " " + " ".join(extra_words)` when extra_words is non-empty
- Flags (--details, --slug, etc.) parsed naturally by typer; `--` separator works for free
- Backward compatible: quoted titles still work (extra_words stays empty)
- Help text: metavar="WORDS" for clean `Usage: tasker new [OPTIONS] TITLE [WORDS]...`
