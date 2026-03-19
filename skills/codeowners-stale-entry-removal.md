---
name: codeowners-stale-entry-removal
description: Remove stale path entries from .github/CODEOWNERS that point to non-existent
  directories. Use when a CODEOWNERS audit flags entries for directories that were
  moved or renamed.
category: ci-cd
date: 2026-03-03
version: 1.0.0
user-invocable: true
---
# CODEOWNERS Stale Entry Removal

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-03-03 |
| **Objective** | Remove stale `/agents/` entry from `.github/CODEOWNERS` pointing to a non-existent top-level directory |
| **Outcome** | Single-line deletion; existing `/.claude/` entry already covers agent configurations |

## When to Use This Skill

Use this pattern whenever:
- A quality audit flags a CODEOWNERS entry for a directory that does not exist
- A directory was moved/renamed (e.g., `/agents/` → `/.claude/agents/`) and the old path was never cleaned up
- CODEOWNERS has redundant entries (old path AND new path both listed)
- CI or repo tooling warns about unresolvable CODEOWNERS patterns

## Root Cause

CODEOWNERS entries for non-existent paths are silently ignored by GitHub but cause confusion:
- Reviewers appear assigned for paths that match nothing
- Audits flag the repo as misconfigured
- The entry persists because there is no automated enforcement that paths must exist

In this case, `/agents/` was the original location before agent configs moved to `/.claude/agents/`.
The `/.claude/` wildcard entry already covers everything under `.claude/`, so `/agents/` was
purely redundant AND stale.

## Verified Workflow

### 1. Confirm the stale entry exists

```bash
grep -n '/agents/' .github/CODEOWNERS
# Expected: line 32: /agents/ @HomericIntelligence/projectscylla-maintainers
```

### 2. Verify the directory does NOT exist

```bash
ls -la | grep agents
# Expected: no output (directory absent)
```

### 3. Verify the replacement path IS covered

```bash
grep '/.claude/' .github/CODEOWNERS
# Expected: /.claude/ @HomericIntelligence/projectscylla-maintainers
ls .claude/agents/
# Expected: agent config files present
```

### 4. Remove the stale line (Edit tool preferred)

Use the Edit tool to delete just the stale line and its comment block if it becomes empty:

```
old:
# Agent configurations and hierarchy
/.claude/ @HomericIntelligence/projectscylla-maintainers
/agents/ @HomericIntelligence/projectscylla-maintainers

new:
# Agent configurations and hierarchy
/.claude/ @HomericIntelligence/projectscylla-maintainers
```

### 5. Commit and PR

```bash
git add .github/CODEOWNERS
git commit -m "fix(codeowners): Remove stale /agents/ entry

The /agents/ top-level directory does not exist. Agent configurations
are located at /.claude/agents/, which is already covered by the
/.claude/ entry.

Closes #<issue-number>"

git push -u origin <branch>
gh pr create --title "fix(codeowners): Remove stale /agents/ entry" \
  --body "Closes #<issue-number>"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Happened | Why It Failed |
|---------|--------------|---------------|
| N/A — fix was straightforward | — | — |

The only subtlety: confirm `/.claude/` (not `/.claude/agents/`) is listed — the wildcard covers
the full subtree so no new entry is needed.

## Results & Parameters

- **Files changed**: `.github/CODEOWNERS` — 1 line deleted
- **Pre-commit hooks**: All skipped (no Python files changed); `trim-trailing-whitespace` and
  `fix-end-of-files` passed
- **PR**: Merged via auto-merge after CI passes

## Related Skills

- `github-bulk-housekeeping` — batch CODEOWNERS and repo config cleanup
- `quality-fix-formatting` — formatting fixes from quality audits

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | March 2026 (4th) quality audit, Issue 8 of 14 — PR #1369 | Stale `/agents/` entry persisted since Feb 2026 audit despite prior fix attempt in PR #1121 |
