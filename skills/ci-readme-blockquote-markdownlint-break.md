---
name: ci-readme-blockquote-markdownlint-break
description: "Markdownlint CI fails on a specific markdown construct even though pre-commit / plugin-validation passed on the individual file — the CI all-files markdownlint run catches it. Covers (a) MD028 blank line without > inside a multi-paragraph blockquote, and (b) MD018 when a line-wrapped GitHub issue reference like #1234 lands at column 1 and is parsed as a malformed ATX heading. Use when: (1) CI markdownlint job fails on README/docs/skills after an edit, (2) CI log cites MD028 or MD018/no-missing-space-atx, (3) pre-commit or validate_plugins.py passes locally but the CI all-files markdownlint run fails."
category: ci-cd
date: 2026-07-09
version: "1.1.0"
user-invocable: false
verification: verified-ci
history: ci-readme-blockquote-markdownlint-break.history
tags: [ci-cd, markdownlint, readme, blockquote, md028, md018, atx-heading, issue-reference, line-wrap, blank-line, pre-commit, ci-debug]
---

# CI: README Blockquote Continuation Breaks Markdownlint

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-23 |
| **Objective** | Drive PR ProjectHephaestus#1570 to green CI |
| **Outcome** | CI passed after adding missing `>` continuation marker to a blank line inside a README blockquote |
| **Verification** | verified-ci |
| **History** | [changelog](./ci-readme-blockquote-markdownlint-break.history) |

A multi-paragraph blockquote in Markdown requires every blank separator line between
paragraphs to start with `>`. Without it, the renderer (and markdownlint) treats the
blank line as ending the blockquote, starting a new one, which violates MD028
(no-blanks-in-blockquote) and can also trip MD009/MD012. The fix is a single-character
`>` on the otherwise-empty line.

## When to Use

- CI markdownlint job fails on README.md after editing or adding a blockquote block
- A blockquote you intended as one unit renders as two separate blockquotes
- `pre-commit run --files README.md` passes locally but CI `--all-files` catches the violation
- CI log cites MD028 or a blank-line rule inside a blockquote in README.md or another doc file
- CI log cites **MD018/no-missing-space-atx** and points at a line that starts with `#<digit>` (e.g. `#1819`) — a line-wrapped GitHub issue reference parsed as a malformed ATX heading
- `python3 scripts/validate_plugins.py` passed but the CI `markdownlint` job still failed on a skill/doc `.md` — plugin-validation-green is NOT markdownlint-green

## Verified Workflow

### Quick Reference

```bash
# Find broken blockquotes — look for blank lines inside a blockquote block without >
grep -n "^>" README.md | head -30
# Spot a gap in line numbers that corresponds to a blank line between > lines

# Fix: every blank line inside a blockquote must start with >
# Before (broken):
# > First paragraph of the note.
#                                   <- blank line WITHOUT >
# > **Note on naming.**  ...
#
# After (fixed):
# > First paragraph of the note.
# >                                  <- blank line WITH >
# > **Note on naming.**  ...

# Verify locally before pushing
pre-commit run markdownlint --files README.md
```

### Detailed Steps

1. Open README.md and locate the blockquote block that spans multiple paragraphs.
2. Find blank lines inside the blockquote that are missing the `>` prefix.
   A symptom: `grep -n "^>" README.md` shows non-consecutive line numbers in the middle of a blockquote.
3. Add `>` (optionally with a space: `> `) to every blank separator line inside the blockquote.
4. Run `pre-commit run markdownlint --files README.md` to confirm the rule passes locally.
5. Commit the fix and push — CI markdownlint gate should go green.

### MD018: line-wrapped issue reference parsed as a heading

A different construct produces the same "CI markdownlint failed but my local check passed"
symptom. When a bold sentence wraps across lines and the wrap puts a GitHub issue reference
at column 1, markdownlint reads that line as an ATX heading with no space after `#` and raises
**MD018/no-missing-space-atx**. Example — the second line begins with `#1819`:

```markdown
**The verified workaround ... :** (drove epic #1809's
#1819→#1823 cleanup wave ...).
```

CI failed at `<file>.md:101:1 MD018`. Note that `python3 scripts/validate_plugins.py` PASSED
(634/634) because it never invokes markdownlint, and pre-commit on the individual file did not
surface it — only the CI `markdownlint` job and `markdownlint-cli2 <file>` caught it.

Fix: ensure **no line starts with `#<digit>`**. Detect and assert empty:

```bash
# MUST print nothing — any hit is a line-leading issue ref that markdownlint reads as a heading
grep -nE '^#[0-9]' <file>.md

# Then confirm zero markdownlint errors (repo config is honored automatically)
markdownlint-cli2 <file>.md   # look for "Summary: 0 error(s)"
```

Reflow the wrap so a non-`#` word leads the line (move a word up), or inline-code the reference
(`` `#1819` ``) so it can't be mistaken for a heading. A one-shot reflow is not enough — pulling
`#1809's` down can just relocate the `#<digit>` to the start of the next wrapped line. Trust the
`grep -nE '^#[0-9]'` = EMPTY assertion, not "I moved the wrap once."

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Running pre-commit on changed files only | `pre-commit run --files <diff-files>` passed, so the blockquote issue was not caught before push | pre-commit scoped to the diff did not catch the blank-line-without-> syntax because... actually it would have caught it if README was in the diff — the root cause was the fix was missing from an earlier commit | Always run `pre-commit run markdownlint --files README.md` any time README blockquotes are edited |
| Trusting `validate_plugins.py` as the markdownlint gate | Ran `python3 scripts/validate_plugins.py` (634/634 pass) and pushed a skill `.md` | `validate_plugins.py` does not invoke markdownlint, so it green-lit a file the CI `markdownlint` job rejected (MD018 at `<file>.md:101:1`) | Plugin-validation-green ≠ markdownlint-green. Run `markdownlint-cli2 <file>.md` locally on any doc/skill edit before pushing |
| Reflowing the wrapped line once | Moved `#1809's` down to the next line to un-wrap the offending line | The reflow just relocated the `#<digit>` to column 1 of the newly-wrapped line — `grep -nE '^#[0-9]'` still matched, MD018 still fired | Assert `grep -nE '^#[0-9]' <file>` returns EMPTY (not "I moved the wrap once"); wrap or inline-code (`` `#N` ``) any `#N` that would otherwise begin a line |

## Results & Parameters

The fix for PR #1570 / issue #1554 was a single-character change in README.md:

```diff
 > Upgrading? When moving across a major version, read the
 > [migration guide](docs/MIGRATION.md) for required consumer changes.
-
+>
 > **Note on naming.** `pip install hephaestus` installs the
 > `HomericIntelligence-Hephaestus` distribution...
```

The blank line between the two blockquote paragraphs lacked the `>` prefix. Markdownlint
flagged this as a rule violation (MD028 / no-blanks-in-blockquote). The CI commit was
`c7883e49` on branch `1554-auto-impl`.

Key invariant: every blank line inside a Markdown blockquote that continues the blockquote
must start with `>`. A blank line without `>` terminates the blockquote.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | PR #1570 / Issue #1554 — packaging scaffolding + MIGRATION link | CI markdownlint gate went green after adding `>` to blank continuation line; commit c7883e49 |
| ProjectMnemosyne | Skill PR #3022 — line-wrapped issue ref `#1819` at column 1 | CI `markdownlint` failed MD018 at `<file>.md:101:1` while `validate_plugins.py` passed 634/634; went green after reflowing so no line starts with `#<digit>` (`grep -nE '^#[0-9]'` empty) |
