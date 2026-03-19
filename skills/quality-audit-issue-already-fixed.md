---
name: quality-audit-issue-already-fixed
description: Verify and close quality audit issues that reference problems already
  resolved in the codebase
category: documentation
date: 2026-03-03
version: 1.0.0
user-invocable: false
---
# Quality Audit Issue Already Fixed

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-03-03 |
| Category | documentation |
| Objective | Verify and close quality audit issues that reference problems already resolved in the codebase |
| Outcome | SUCCESS — read file first, confirmed fix already present, verified issue closed, no spurious edit made |
| Issue | #1347 (fix(docs): garbled docstring in scylla/analysis/__init__.py) |

## When to Use

Trigger this skill when:
- A quality audit issue references a file problem (garbled text, bad docstring, fragment, etc.)
- The issue notes "recurring" or "prior fix attempted"
- The branch/worktree is named `<number>-auto-impl` and was pre-created by automation
- The issue references a specific prior commit or PR that "fixed" the problem

**Do NOT use this skill** when:
- The file clearly still contains the problem described
- The issue is newly filed without a prior fix attempt

## Verified Workflow

### Step 1: Read the target file first

```bash
# Read the exact lines cited in the issue BEFORE touching anything
head -10 scylla/analysis/__init__.py
```

Check whether the problem described in the issue still exists. If it does not, proceed to Step 2.

### Step 2: Confirm with git log

```bash
git log --oneline -5
```

Look for a commit message matching the issue title. If a matching commit exists and predates the branch point, the fix was already merged.

### Step 3: Check the issue state

```bash
gh issue view <number> --json state -q '.state'
```

If `CLOSED`, no work needed. If `OPEN` but the file is clean, post a comment and close.

### Step 4: Check for an open PR on the branch

```bash
gh pr list --head <branch-name>
```

If no open PR and no remaining work, the session is complete.

### Step 5: Do nothing (or close the issue)

If the fix is confirmed present:
- Do **not** edit the file
- Do **not** create a PR
- Optionally post a closing comment on the issue if it is still OPEN

## Failed Attempts

None in this session — the verify-before-edit pattern was followed correctly from the start. The common failure mode (not captured here but anticipated) is:

- **Editing a file that does not need editing** — making a cosmetic change just to "have something to commit," which introduces noise and a spurious PR.
- **Missing the issue is already CLOSED** — blindly following the prompt to "create a PR" without checking issue state.

## Results & Parameters

### Session Summary

- **Issue**: #1347 — "Fix garbled docstring in scylla/analysis/__init__.py"
- **Trigger**: `.claude-prompt-1347.md` auto-impl prompt in worktree `issue-1347`
- **Branch**: `1347-auto-impl`
- **File examined**: `scylla/analysis/__init__.py` lines 1–6
- **Finding**: Docstring was already clean — no Mojo migration fragment present
- **Confirming commit**: `510c93c3 fix(docs): Fix garbled docstring in scylla/analysis/__init__.py`
- **Issue state**: CLOSED
- **Action taken**: None (correct)

### Key Decision Point

The prompt said "The issue persists in the current codebase (commit c88692b)" — but `c88692b` was an *earlier* commit. The fix landed at `510c93c3` (HEAD at the time). Always read the actual file rather than trusting the issue description's claim about current state.

### Diagnostic Commands

```bash
# Confirm file state
head -10 scylla/analysis/__init__.py

# Confirm fix commit exists
git log --oneline --grep="garbled"

# Confirm issue state
gh issue view 1347 --json state -q '.state'
```
