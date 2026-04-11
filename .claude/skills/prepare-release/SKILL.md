---
name: prepare-release
description: Prepare a new mcp-tasker release: bump version, update README/DESIGN, refresh lockfile, run tox. Use when the user says "prepare a release", "cut a release", "bump the version", or invokes /prepare-release.
---

# prepare-release

A **tier-1** release skill: mutate files, run checks, print next steps. Never run `git commit`, `git tag`, or `git push`. The user reviews the diff and ships manually.

Optional argument: `major`, `minor`, `patch`, or an explicit `X.Y.Z` — pre-seeds the version decision. If absent, reason about the bump from commits.

---

## Flow overview

```
1. Pre-flight checks
2. Detect baseline tag
3. Read commits since baseline
4. GATE 1: propose version, get approval
5. Draft README patch notes
6. Check DESIGN.md drift, draft edits if implicated
7. GATE 2: approve notes + design together
8. Write pyproject.toml, README.md, DESIGN.md
9. uv lock --upgrade
10. uv run tox (with one retry on skill-caused failures)
11. Print final output with suggested git commands
```

Every step has a stop condition. When a stop condition fires, leave whatever has been written on disk, print why, and exit. Do not attempt to roll back file changes — the user will review via `git diff`.

---

## 1. Pre-flight checks

Before mutating any files, verify the working state.

**Check A — tracked-file cleanliness.** Run `git status --porcelain`. If any line starts with `M`, `A`, `D`, `R`, or `C` (tracked file modifications), the tree is dirty. Untracked files (`??`) are ignored.

**Check B — on main branch.** Run `git rev-parse --abbrev-ref HEAD`. If not `main`, stop candidate.

On either failure, prompt the user interactively: show the specific problem (file list for dirty, branch name for wrong branch) and ask `Proceed anyway? [y/N]`. Default is no. Only proceed on explicit `y`.

No `--force` flag. The interactive prompt is the only override path.

## 2. Detect the baseline tag

The baseline tag defines "previous release" — the point from which commits are diffed.

Algorithm:
1. Read the current version from `pyproject.toml` (`[project] version = "X.Y.Z"`).
2. Look for a tag `vX.Y.Z` matching that version. If found, that's the baseline.
3. Otherwise, list all tags matching `vX.Y.Z` (stable only — exclude anything with `a`, `b`, `rc` suffixes) and find the highest one ≤ the pyproject version. That's the baseline.
4. If multiple tags could plausibly match, or nothing is resolvable, **ask the user** which tag to use as baseline. Do not guess.

**Stop conditions:**
- No prior stable release tag exists at all → stop. "No prior release tag found; prepare-release assumes an existing release baseline. First releases must be cut manually."
- Ambiguity the user cannot resolve → stop.

## 3. Read commits since baseline

Run `git log --no-merges --format="%H %s" <baseline>..HEAD` to get the commit list.

**Stop condition:** if the list is empty, stop. "Nothing to release since `<baseline>`."

Store the commit list — you'll need the subjects for version reasoning and the full messages (+ optional diffs) for ambiguous cases and DESIGN drift detection.

## 4. GATE 1 — propose a version

Goal: decide major / minor / patch, propose a specific `X.Y.Z`, justify it in prose, get explicit user approval.

**Reasoning approach:**
- Read all commit subjects.
- For commits with vague prefixes (`ref:`, `chore:`, `update`, no prefix), read the commit body or run `git show --stat <hash>` to understand what actually changed.
- Apply standard semver: breaking changes → major; new user-visible features → minor; bug fixes + internal refactors → patch.
- Watch for hidden breaking changes: dependency bumps that drop support for a Python version, CLI flag removals, file format changes, MCP tool signature changes. A commit titled `ref:` can still break users.
- If the user passed an argument (`major` / `minor` / `patch` / `X.Y.Z`), use it and skip the reasoning — but still show a one-line summary of commits and wait for approval.

**Prefix tally as sanity check:** count prefixes (`feat:`, `fix:`, etc.). If the tally disagrees with the proposed bump (e.g., 5 `feat:` commits but proposing patch), flag the disagreement in the reasoning rather than silently overriding.

**Output format for the gate:**

```
Commits since v1.3.0 (2):
  - ref: implicit closed display to explicit --closed flag
  - fix: don't show non-todo tasks on list --todo

Proposed: 1.3.1 (patch)
Reasoning: One bug fix and one refactor of an existing CLI flag.
The --closed change is additive (new explicit flag), not a removal,
so existing invocations still work. No user-visible new features,
no breaking changes. Patch bump fits.

Approve [1.3.1], or override (e.g., "1.4.0", "minor", "major")?
```

**Override validation:**
- Lower than current → refuse. "Cannot bump to X.Y.Z — not greater than current A.B.C."
- Already has a tag (`git rev-parse vX.Y.Z` succeeds) → refuse. "Version X.Y.Z already released."
- Prerelease format (`1.4.0a1`, `2.0.0rc2`) → allow but warn: "Prereleases are not typically added to README release notes. Write a `### X.Y.Z` section anyway? [y/N]". If no, skip README patch notes for this run but still bump pyproject.
- Any valid greater stable semver → accept.

Always ask, even when an argument was passed. No silent auto-accept.

## 5. Draft README patch notes

Goal: produce a new `### X.Y.Z` section in `README.md`'s `## Release Notes` that matches the house style.

**Learn the style:** read the two most recent release sections (`### 1.3.0` and `### 1.2.0` at time of writing) to calibrate voice, bullet phrasing, grouping conventions, and prefixes.

**House style observed (verify by reading — this may drift):**
- Flat bullet list, no sub-headings.
- Themed via inline prefixes: `MCP:`, `Build:`, `Bug fixes:`.
- User-facing phrasing — not commit subjects verbatim. `ref: implicit closed display to explicit --closed flag` becomes something like `` `list --closed` flag to show recently closed tasks (previously shown implicitly) ``.
- Ordered roughly: new features → improvements → MCP changes → Build/infra → Bug fixes.
- Past/present tense is loose; match whatever the last release used.

**Drafting rules:**
- Curate, don't enumerate. Collapse related commits into one bullet. Drop commits that are pure internal churn (version bumps, tox config tweaks, CI noise) unless they affect users.
- Group bug fixes under a single `Bug fixes:` bullet with comma-separated items, matching the existing pattern.
- Keep bullets short — one line each is the norm.

## 6. DESIGN.md drift check

Goal: keep `DESIGN.md` honest about the current app state, but only touch sections this release actually affects.

**Step 1 — is DESIGN.md implicated at all?** Scan the release's commits. DESIGN.md is implicated if commits touch:
- CLI command surface (new commands, new flags, changed behavior of existing commands)
- Task file format (filenames, IDs, metadata, statuses)
- MCP tool list or tool signatures
- Status lifecycle (pending / in-progress / in-review / done / cancelled)
- Anything else explicitly documented in DESIGN.md

If no commits match, **skip this step entirely** and report: "DESIGN.md: no drift detected for this release."

**Step 2 — surgical edits.** For each implicated area:
1. Grep the actual source for the current surface (e.g., `grep` Typer commands in `src/tasker/main.py` or wherever commands live, MCP tools in the MCP server module).
2. Read the matching section of `DESIGN.md`.
3. Identify the specific lines that are stale and propose minimal edits — new row in a table, one new bullet, one updated sentence.

Do **not** rewrite whole sections. Do **not** "improve" prose that is merely dated in style rather than factually wrong. Do **not** audit unrelated sections just because they happen to be nearby.

**Scope discipline:** only check drift caused by *this release's* commits. A full DESIGN.md vs source audit is a separate concern and out of scope for this skill.

## 7. GATE 2 — approve notes + design together

Show the drafted README section and the proposed DESIGN.md edits in one combined gate. Do not write files yet.

**Output format:**

```
=== README.md ===

### 1.3.1
- `list --closed` flag to explicitly show recently closed tasks (previously implicit)
- Bug fixes: `list --todo` no longer shows non-TODO tasks

=== DESIGN.md ===

No drift detected for this release.

Approve both, revise (say what to change), or reject?
```

**Revision handling:**
- On specific feedback ("group MCP separately", "don't mention the flag rename, it's internal") → redraft and show the gate again.
- After 2 redrafts on the same gate, stop and say: "Deferring to manual edit — write the notes/design changes yourself, then re-run /prepare-release to continue from the file-write step." The skill's idempotency (see §9) will resume correctly.
- On outright rejection → stop with the same manual-edit deferral.

## 8. Write the files

Only after both gates are approved:
1. Update `pyproject.toml`: change the `version = "X.Y.Z"` line under `[project]`. Do not touch anything else in that file.
2. Prepend the new `### X.Y.Z` section to `README.md`'s `## Release Notes` (directly above the previous release entry).
3. Apply the DESIGN.md edits if any.

## 9. Idempotent re-run detection

The skill may be re-invoked mid-flow — e.g., tox failed, user fixed something, runs `/prepare-release` again. Detect this at **step 1** and adapt:

**In-progress release signal:** `pyproject.toml` version is greater than the highest stable tag *and* `README.md` already has a `### <that version>` section.

When detected:
- Skip GATE 1 (version already decided).
- Skip README drafting unless the user asks to revise it.
- Skip DESIGN.md drafting unless they asked to revise that too.
- Resume at `uv lock --upgrade` → `tox` → final output.
- Announce clearly: "Detected in-progress release X.Y.Z — resuming from lockfile step."

The user can force a fresh run by manually reverting `pyproject.toml` before re-invoking.

## 10. Refresh dependencies

Run `uv lock --upgrade`. This refreshes `uv.lock` against the newest versions allowed by the existing constraints in `pyproject.toml`.

**Do not** edit constraint floors (`typer>=0.12.0`) or ceilings (`jinja2 (>=3.1.6,<4.0.0)`) in `pyproject.toml`. Raising floors is a support-policy decision; ceilings exist because upstream has known breakage. If `uv lock --upgrade` surfaces newer versions that are blocked by ceilings, mention it in the final output as an FYI — do not act on it.

**Stop condition:** if `uv lock --upgrade` fails (resolution conflict, network error, etc.), stop immediately. Print the error. "Release blocked by dep resolution. Fix constraints manually and re-run."

## 11. Run tox

Run `uv run tox`. This is the acceptance gate.

**On success:** proceed to final output.

**On failure:** look at the failure output. Two cases:

**Case A — plausibly caused by this skill's edits.** Formatting (`black`), import sort (`isort`), trailing whitespace, line-too-long in README.md, simple type errors on files the skill touched. Apply the fix (run `uv run black`, `uv run isort`, or edit the offending line) and re-run `uv run tox` **once**. If still red, stop.

**Case B — not caused by this skill.** Test failures in unrelated code, type errors in source files the skill didn't touch, tool version incompatibilities, missing test fixtures. Stop immediately. "Tox failure unrelated to release prep — fix and re-run. Pre-existing failures are out of scope for this skill."

Never skip hooks, never `--no-verify`, never edit `tox.ini` to quiet errors.

## 12. Final output

On success, print a single summary block:

```
Release prep complete: vX.Y.Z

Changed files:
  pyproject.toml       <N> +, <M> -
  uv.lock              <N> +, <M> -
  README.md            <N> +
  DESIGN.md            <N> +, <M> -   (or: unchanged)

Tox: passed

Suggested next steps (run yourself):
  git add pyproject.toml uv.lock README.md DESIGN.md
  git commit -m "<commit message in house style>"
  git tag vX.Y.Z
  git push && git push --tags
```

**Commit message style:** read the most recent release commit (search `git log` for the commit that last bumped the version in `pyproject.toml`) and match its phrasing. At time of writing, the style is `update to version X.Y.Z` — verify this is still current rather than assuming.

Do **not** execute any `git` command. Print and stop.

---

## Stop conditions — quick reference

| When | Action |
|---|---|
| Dirty tracked tree, user declines override | Stop, report dirty files |
| Not on `main`, user declines override | Stop, report branch |
| No baseline tag found | Stop, "first releases must be cut manually" |
| Baseline ambiguous and user cannot resolve | Stop, ask what they want |
| Zero commits since baseline | Stop, "nothing to release" |
| User overrides to version ≤ current or already tagged | Refuse override, ask again |
| User rejects GATE 1 outright | Stop |
| GATE 2 hits 2-redraft limit or outright rejection | Stop, defer to manual edit |
| `uv lock --upgrade` fails | Stop, report error |
| Tox fails and cause is not skill-caused | Stop, "fix pre-existing and re-run" |
| Tox still fails after one auto-fix retry | Stop, report remaining issues |

## What this skill never does

- Never runs `git commit`, `git tag`, `git push`, or any other mutating git command.
- Never edits `pyproject.toml` constraints (only the `version` field).
- Never touches `tox.ini` or CI configuration.
- Never uses `--no-verify`, `--no-gpg-sign`, or equivalent skip-hook flags.
- Never rewrites DESIGN.md sections that aren't implicated by this release.
- Never silently auto-accepts a version bump — always asks.
- Never edits files outside: `pyproject.toml`, `uv.lock`, `README.md`, `DESIGN.md`.
