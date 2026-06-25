---
name: ci-readme-blockquote-markdownlint-break
description: "Markdownlint CI fails when a multi-paragraph blockquote in README.md is missing the > continuation marker on blank lines between paragraphs. Use when: (1) CI markdownlint job fails on README after adding or editing a blockquote, (2) a blockquote renders as two separate blocks when you intended one, (3) pre-commit markdownlint passes on individual files but CI all-files run fails with MD028 or blank-line-in-blockquote."
category: ci-cd
date: 2026-06-23
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [ci-cd, markdownlint, readme, blockquote, md028, blank-line, pre-commit, ci-debug]
---

# CI: README Blockquote Continuation Breaks Markdownlint

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-23 |
| **Objective** | Drive PR ProjectHephaestus#1570 to green CI |
| **Outcome** | CI passed after adding missing `>` continuation marker to a blank line inside a README blockquote |
| **Verification** | verified-ci |

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

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Running pre-commit on changed files only | `pre-commit run --files <diff-files>` passed, so the blockquote issue was not caught before push | pre-commit scoped to the diff did not catch the blank-line-without-> syntax because... actually it would have caught it if README was in the diff — the root cause was the fix was missing from an earlier commit | Always run `pre-commit run markdownlint --files README.md` any time README blockquotes are edited |

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
