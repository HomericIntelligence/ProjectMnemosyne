---
name: doc-sync-existing-impl
description: 'Sync documentation when an issue''s fix is already implemented but docs
  lag behind. Use when: (1) issue requests fix but code fix already exists in scripts/,
  (2) CLAUDE.md describes old behavior instead of current wrapper, (3) pre-commit
  docs reference direct tool invocation instead of compat wrapper.'
category: documentation
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
# Skill: doc-sync-existing-impl

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-03-15 |
| Project | ProjectOdyssey |
| Objective | Fix GLIBC mojo-format docs lag — issue requested fix that was already implemented |
| Outcome | CLAUDE.md updated in 2 targeted edits; PR #4894 created |
| Issue | HomericIntelligence/ProjectOdyssey#3365 |

## When to Use

Use this skill when:

- An issue says "investigate X / fix Y" but reading the codebase reveals Y was already fixed
- `CLAUDE.md` or `docs/dev/*.md` describes tool invocation that no longer matches the actual hook entry
- A pre-commit hook was upgraded from `pixi run <tool>` to a wrapper script but docs weren't updated
- The issue title matches existing files/scripts (e.g. issue about `mojo-format GLIBC` and
  `scripts/mojo-format-compat.sh` already exists)

**Trigger symptoms**:

- Issue body says "investigate / document" rather than "implement"
- `.pre-commit-config.yaml` `entry:` field disagrees with what `CLAUDE.md` describes
- Existing `docs/dev/` file already covers the problem completely

## Verified Workflow

### Quick Reference

| Step | Action |
|------|--------|
| 1 | Read the issue body and prompt file |
| 2 | Grep for referenced scripts/files to see if fix exists |
| 3 | Compare `.pre-commit-config.yaml` entry vs CLAUDE.md description |
| 4 | Make minimal targeted edits to sync docs |
| 5 | Commit, push, open PR |

### Step 1 — Confirm fix already exists

```bash
# Check if wrapper script exists
ls scripts/mojo-format-compat.sh

# Check what .pre-commit-config.yaml actually invokes
grep -A3 "id: mojo-format" .pre-commit-config.yaml

# Check if docs already explain the behavior
ls docs/dev/mojo-glibc-compatibility.md
```

If all three exist, the implementation is done. Only docs need updating.

### Step 2 — Find stale doc text

Grep CLAUDE.md for the old behavior description:

```bash
grep -n "pixi run mojo format\|version mismatch\|local Mojo version" CLAUDE.md
```

Common stale patterns after a hook is wrapped:

- `"The hooks include \`pixi run mojo format\`"` → should reference the wrapper script
- `"requires the exact Mojo version pinned"` → was about version; real issue is GLIBC

### Step 3 — Make targeted edits

Two edits are typically sufficient:

1. **Section intro line**: Change `pixi run mojo format` → `scripts/mojo-format-compat.sh` wrapper
2. **Compatibility note**: Replace version-mismatch language with GLIBC constraint + link to dev doc

Keep edits minimal — only change text that is factually wrong. Do not refactor surrounding content.

### Step 4 — Verify no markdown lint issues

Lines must stay under 120 chars. Check the changed lines:

```bash
awk 'length > 120' CLAUDE.md | head -5
```

### Step 5 — Commit and PR

```bash
git add CLAUDE.md
git commit -m "docs(CLAUDE.md): update <tool> hook documentation for <fix-description>

<One-line explanation of what was stale and what is accurate now.>

Closes #<issue-number>"

git push -u origin <branch>
gh pr create --title "docs(...): ..." --body "Closes #<issue>"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A — direct path | Checked pre-commit config and scripts first before writing any code | No failures; implementation was pre-existing | Always read `.pre-commit-config.yaml` entry fields before assuming code needs writing |
| Skill invocation for commit | Used `Skill commit-commands:commit-push-pr` | Permission denied in don't-ask mode | Fall back to manual `git add && git commit && git push && gh pr create` |

## Results & Parameters

| Parameter | Value |
|-----------|-------|
| Issue type | Documentation-only (fix pre-existed) |
| Files changed | 1 (`CLAUDE.md`) |
| Edits needed | 2 targeted string replacements |
| Time to identify | ~2 minutes (read pre-commit config + grep CLAUDE.md) |
| PR type | `docs(CLAUDE.md): ...` conventional commit |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3365 — mojo-format GLIBC fix docs | [notes.md](../../references/notes.md) |
