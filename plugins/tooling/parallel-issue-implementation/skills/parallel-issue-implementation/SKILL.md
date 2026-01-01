---
name: parallel-issue-implementation
description: "Implement multiple GitHub issues in parallel using git worktrees. Use when you have 2+ issues with detailed plans ready for implementation."
category: tooling
source: ProjectScylla
date: 2025-01-01
---

# Parallel Issue Implementation with Worktrees

Implement multiple GitHub issues simultaneously using git worktrees for isolation.

## Overview

| Date | Objective | Outcome |
|------|-----------|---------|
| 2025-01-01 | Implement 4 GitHub issues with detailed plans in parallel | All 4 PRs created and merged successfully |

## When to Use

- (1) Multiple issues have detailed implementation plans in comments
- (2) Issues are independent (no dependencies between them)
- (3) You want to maximize throughput by working in parallel
- (4) Each issue touches different files (minimal conflicts)

## Verified Workflow

### Phase 1: Discovery

```bash
# List open issues
gh issue list --state open --json number,title,labels

# Read issue with implementation plan (plans are often in comments!)
gh issue view <number> --comments
```

### Phase 2: Create Worktrees (2 at a time recommended)

```bash
# Create worktrees for first batch
git worktree add ../ProjectName-<issue1> -b <issue1>-<description> main
git worktree add ../ProjectName-<issue2> -b <issue2>-<description> main
```

### Phase 3: Parallel Implementation

1. Read all files needed for BOTH issues simultaneously
2. Make edits in parallel (use Edit tool on different worktree paths)
3. Run tests in parallel for both worktrees

```bash
# Tests in parallel (different terminals or background)
cd /path/to/worktree-1 && pixi run pytest tests/ -v
cd /path/to/worktree-2 && pixi run pytest tests/ -v
```

### Phase 4: Commit and PR Creation

```bash
# Commit in each worktree
cd /path/to/worktree-1 && git add -A && git commit -m "type(scope): description

Closes #<issue>"

# Push and create PR
git push -u origin <branch>
gh pr create --title "Title" --body "$(cat <<'EOF'
## Summary
...

Closes #<issue>

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

### Phase 5: Merge and Cleanup

```bash
# Merge PRs
gh pr merge <pr-number> --rebase --delete-branch

# After all merged, cleanup worktrees (manual step required)
git worktree remove /path/to/worktree-1
git worktree remove /path/to/worktree-2
git branch -D <branch1> <branch2>

# Update main
git fetch --prune origin
git pull --rebase
```

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|------------|--------|
| Auto-merge with `gh pr merge --auto` | Branch protection rules not configured | Use manual `gh pr merge --rebase` instead |
| Automated worktree removal in script | Safety net blocks `git worktree remove --force` | Provide manual cleanup commands to user |
| Delete branches immediately after PR merge | Worktrees still reference the branches | Must remove worktrees BEFORE deleting branches |
| Working on 4 issues simultaneously | Context switching overhead too high | Batch in groups of 2 for optimal throughput |

## Results & Parameters

### Optimal Batch Size

- **2 issues at a time**: Best balance of parallelism vs context
- Read files for both issues upfront
- Make all edits before running tests
- Run tests in parallel

### Worktree Naming Convention

```
../ProjectName-<issue-number>
```

Example: `../ProjectScylla-90`, `../ProjectScylla-91`

### Branch Naming Convention

```
<issue-number>-<kebab-case-description>
```

Example: `90-standardize-runs-per-tier`

### Success Metrics (This Session)

| Metric | Value |
|--------|-------|
| Issues implemented | 4 |
| PRs created | 4 |
| PRs merged | 4 |
| Files changed | 15 |
| Lines added | 433 |
| Lines removed | 32 |

## References

- See `worktree-create` for worktree creation patterns
- See `gh-create-pr-linked` for PR creation with issue linking
- See `gh-read-issue-context` for reading issue plans from comments
