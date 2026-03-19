---
name: verify-issue-already-implemented
description: 'Verify whether a GitHub issue has already been implemented before starting
  work. Use when: assigned to implement a GitHub issue, before writing any code, when
  working in a worktree that may have prior commits.'
category: architecture
date: 2026-03-05
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Name** | verify-issue-already-implemented |
| **Category** | architecture |
| **Trigger** | Start of any issue implementation task |
| **Output** | Decision: implement vs report already done |

## When to Use

- When assigned to implement a GitHub issue via a `.claude-prompt-<N>.md` file
- When working in a named worktree branch (e.g. `<issue>-auto-impl`)
- Before searching for code to change or writing any new code
- When the branch name suggests prior automated work was done on the issue

## Verified Workflow

### Step 1: Check git log for issue reference

```bash
git log --oneline -20 | grep -i "<issue-number>\|Closes #<issue-number>"
```

If a commit references the issue number (e.g. `Closes #3112`), the work is already done.

### Step 2: Verify no remaining patterns exist

Search for the specific pattern the issue targets:

```bash
# Example: for a matmul standardization issue
grep -r "__matmul__(" --include="*.mojo" tests/ shared/ papers/
```

If no matches found AND a prior commit exists, the issue is fully implemented.

### Step 3: Check for existing PR

```bash
gh pr list --head <branch-name>
```

If a PR already exists and references the issue, report completion — do not create a duplicate PR.

### Step 4: Report status

Post to the GitHub issue if still open:

```bash
gh issue view <number> --json state -q .state
gh issue comment <number> --body "Issue already implemented in commit <sha> and PR #<pr>."
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Immediately searching for patterns | Searched codebase for `.__matmul__(` before checking git log | Would have found nothing and been confused | Always check git log first — a prior commit may have already done the work |
| Assuming worktree is fresh | Assumed `3112-auto-impl` branch had no prior commits | The branch had commit `86b485a3` already closing the issue | Named worktree branches often have auto-impl commits already applied |

## Results & Parameters

### Canonical check sequence

```bash
# 1. Check recent commits for issue reference
git log --oneline -20

# 2. Check for existing PR on this branch
gh pr list --head "$(git branch --show-current)"

# 3. Search for remaining instances of the target pattern
grep -r "<target-pattern>" --include="*.mojo" .

# 4. If already done: report and exit
echo "Issue #<N> already implemented. PR exists. No further action needed."
```

### Decision matrix

| git log has "Closes #N" | Pattern search finds results | PR exists | Action |
|-------------------------|------------------------------|-----------|--------|
| Yes | No | Yes | Report done, exit |
| Yes | No | No | Create PR linking to issue |
| Yes | Yes | Any | Investigate — partial implementation |
| No | Yes | No | Implement the issue |
| No | No | No | Implement the issue (may be unrelated) |
