---
name: verify-issue-before-work
description: Verify GitHub issue state and existing implementation before starting work to avoid duplicate effort
---

# Verify Issue Before Work

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2025-12-29 |
| **Objective** | Continue P2 issue implementation, specifically Training Dashboard (#2672) |
| **Outcome** | Wasted effort - Issue was already closed and merged |
| **Root Cause** | Did not verify issue state before starting work |
| **Key Learning** | Always check `gh issue view <number> --json state` and existing code BEFORE planning/implementing |

## When to Use

Use this verification workflow **BEFORE** starting any implementation work:

- User says "continue with [feature]" or "work on issue #XXX"
- Starting work on an issue from a backlog or roadmap
- Resuming work after a break or context switch
- Taking over work from another session

## Verified Workflow

### Step 1: Check Issue State First

```bash
# ALWAYS run this FIRST - before any planning or implementation
gh issue view <issue-number> --json state,title,closedAt

# Example output if closed:
# {"closedAt":"2025-12-29T20:37:46Z","state":"CLOSED","title":"Add Training Dashboard"}

# If state is "CLOSED", STOP and move to next issue
```

### Step 2: Check for Existing Implementation

```bash
# Look for related commits
git log --all --oneline --grep="<issue-number>" | head -5

# Look for feature-specific commits
git log --all --oneline --grep="<feature-keyword>" | head -10

# Check if files exist
ls -la <expected-directory>
```

### Step 3: Verify with PR Search

```bash
# Check for merged PRs
gh pr list --search "<feature-keyword>" --state merged --json number,title

# Check for open PRs
gh pr list --search "<feature-keyword>" --state open --json number,title
```

### Step 4: Only Then Start Work

If all checks pass (issue open, no existing implementation), proceed with:
- Reading issue details
- Planning implementation
- Creating feature branch

## Failed Attempts

| Attempt | What I Did | What Went Wrong | Why It Failed |
|---------|-----------|-----------------|---------------|
| Started without verification | Updated todo, read issue, searched files, created dirs | Spent 5+ tool calls on already-complete work | Skipped state verification, assumed issue was open |
| File write without read | Tried to write server.py | Tool error - file not read first | Should check file existence first |

### Cost of Failure
- Wasted 7 tool calls
- Wasted ~5 minutes of exploration
- Created duplicate effort

## Results & Parameters

### Correct Verification Sequence

```bash
# 1. Check issue state (< 1 second)
gh issue view 2672 --json state,title,closedAt

# 2. Find related commits (if state was OPEN)
git log --all --oneline --grep="2672"

# 3. Check directory existence
ls -la scripts/dashboard/

# 4. Only if all clear: proceed with implementation
```

### Time Comparison

| Approach | Tool Calls | Time |
|----------|------------|------|
| Without verification | 7 | ~5 minutes wasted |
| With verification | 1 | ~2 seconds |

### Prevention Checklist

Before ANY implementation work:

- [ ] Run `gh issue view <N> --json state` - verify state is "OPEN"
- [ ] Run `git log --grep="<N>"` - check for existing commits
- [ ] Run `ls -la <expected-path>` - verify directory doesn't exist
- [ ] Run `gh pr list --search "<keyword>"` - check for merged PRs
- [ ] Only then: Read issue, plan, implement
