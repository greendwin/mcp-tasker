---
id: s19t2906
slug: defensive-parsing-for-malformed-git
status: pending
---

# Defensive parsing for malformed git ls-files output

In `_parse_unmerged_output` (`src/tasker/git.py`), `line.split("\t", 1)` will raise `ValueError` on a line without a tab. Input comes from git's own format so this can't happen in practice, but a defensive guard (skip malformed lines) would improve robustness.

Low priority — only matters if git output format changes or is corrupted.
