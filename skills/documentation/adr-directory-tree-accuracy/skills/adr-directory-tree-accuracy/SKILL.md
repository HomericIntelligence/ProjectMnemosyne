---
name: adr-directory-tree-accuracy
description: "Update ADR directory tree listings to reflect actual filesystem contents after file deletions or additions. Use when: (1) a file is deleted/added but the ADR still shows the old listing, (2) a GitHub issue requests verifying helpers/tests directories are accurately documented, (3) an ADR directory tree shows only a subset of the files actually present."
category: documentation
date: 2026-03-07
user-invocable: false
---

# Skill: adr-directory-tree-accuracy

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-03-07 |
| Objective | Update ADR-004 directory tree to reflect actual `tests/helpers/` contents after `gradient_checking.mojo` was deleted in a prior PR |
| Outcome | Success — single-file listing replaced with accurate 5-file listing, PR #3820 created and auto-merge enabled |
| Category | documentation |

## When to Use

Use this skill when:

- A file is deleted or added in a PR but the ADR directory tree was not updated alongside that change
- A follow-up issue (e.g., "verify helpers directory" or "clean up after stub deletion") asks you to check whether documentation reflects reality
- `grep` finds a directory tree in an ADR that lists fewer files than `ls` shows on disk
- An issue describes the directory as "possibly empty" or "needing verification" when it actually still contains active files

## Verified Workflow

### 1. Read the issue and confirm the actual state

```bash
gh issue view <number> --comments
ls tests/helpers/     # or the relevant directory
```

Key check: verify whether the deletion actually happened (the file may already be gone from a prior PR).

### 2. Find the stale ADR reference

```bash
grep -n "helpers\|<deleted-file>" docs/adr/ADR-*.md
```

Identify which ADR contains the directory tree and which line needs updating.

### 3. Compare ADR listing vs. actual filesystem

Read the ADR section around the directory tree, then cross-reference with `ls`.
Look for:

- Files listed in the ADR that no longer exist (phantom references)
- Files that exist on disk but are missing from the ADR listing (incomplete listing)

### 4. Update the directory tree

Use the Edit tool to replace the stale listing with an accurate one.
Match the tree format already used in the ADR (ASCII tree with `├──` / `└──` connectors and trailing comments).

Example replacement:

**Before:**
```text
└── helpers/
    └── fixtures.mojo                     # Test fixtures
```

**After:**
```text
└── helpers/
    ├── __init__.mojo                     # Package re-exports
    ├── fixtures.mojo                     # Test fixture utilities
    ├── utils.mojo                        # Tensor debugging utilities
    ├── test_fixtures.mojo                # Self-tests for fixtures.mojo
    └── test_utils.mojo                   # Self-tests for utils.mojo
```

### 5. Validate with markdownlint

```bash
pixi run pre-commit run markdownlint-cli2 --files docs/adr/ADR-*.md
```

### 6. Commit and create PR

```bash
git add docs/adr/ADR-<N>-<name>.md
git commit -m "docs(adr): update ADR-<N> <section> directory tree to reflect active files"
git push -u origin <branch>
gh pr create --title "docs(adr): update ADR-<N> <section> directory tree to reflect active files" \
  --body "Closes #<issue>" --label "documentation"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Searching for `gradient_checking` in ADR-004 | Used `grep` to find stale reference to deleted file | No matches — file was already deleted from ADR in a prior PR | Always check both the filesystem AND the ADR independently; the issue may describe a state that has already been partially fixed |
| Looking for "Related Files" section at a specific line | Issue description referenced line 326 as the location of a stale entry | The line number referenced an earlier state of the file | Don't rely on line numbers from issue descriptions; grep for the actual pattern instead |

## Results & Parameters

| Parameter | Value |
|-----------|-------|
| Files changed | `docs/adr/ADR-004-testing-strategy.md` |
| Lines changed | 1 removed, 5 added |
| Pre-commit hooks | All passed (markdownlint, trailing whitespace, end-of-file) |
| PR | https://github.com/HomericIntelligence/ProjectOdyssey/pull/3820 |
| Issue | #3252 |
| Branch | `3252-auto-impl` |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3252 follow-up from #3061 | [notes.md](../references/notes.md) |

## Key Insight

When an issue says "verify this directory or clean it up," the actual task is often just a
documentation accuracy fix — not code deletion. Confirm the filesystem state first, then update
the ADR to match. The deleted file may already be gone from both disk and the ADR; the remaining
work is ensuring the *rest* of the directory listing is complete and accurate.
