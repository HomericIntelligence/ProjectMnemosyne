---
name: gh-read-issue-context
description: "Read context from GitHub issue including body and comments"
category: tooling
source: ProjectOdyssey
date: 2025-12-30
---

# Read Issue Context

Retrieve all context from a GitHub issue before starting work.

## Overview

| Date | Objective | Outcome |
|------|-----------|---------|
| 2025-12-30 | Gather full context before implementation | Informed decisions based on prior work |

## When to Use

- (1) Before starting implementation work
- (2) When prior context is needed from earlier work
- (3) Resuming work after a break and need to understand decisions
- (4) Checking if issue has been partially addressed

## Verified Workflow

1. **Get issue details**: `gh issue view <number>`
2. **Read all comments**: `gh issue view <number> --comments`
3. **Check linked PRs**: `gh pr list --search "issue:<number>"`
4. **Note key context**: Design decisions, blockers, acceptance criteria

## Results

Copy-paste ready commands:

```bash
# Get issue details
gh issue view <number>

# Get issue with all comments (implementation history)
gh issue view <number> --comments

# Get structured JSON for parsing
gh issue view <number> --json title,body,comments,labels,assignees,milestone,state

# Get specific field
gh issue view <number> --json body --jq '.body'

# Get linked PRs
gh pr list --search "issue:<number>"

# Get issue timeline
gh api repos/{owner}/{repo}/issues/<number>/timeline
```

### Data Extraction

```bash
# Title only
gh issue view <number> --json title --jq '.title'

# Body content
gh issue view <number> --json body --jq '.body'

# Labels as list
gh issue view <number> --json labels --jq '.labels[].name'

# Comment bodies
gh issue view <number> --json comments --jq '.comments[].body'

# Comment count
gh issue view <number> --json comments --jq '.comments | length'
```

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|------------|--------|
| Only read issue body, skipped comments | Missed important design decisions from discussions | Always read comments - they contain implementation history |
| Didn't check for existing PRs | Duplicated work that was already done | Check `gh pr list --search "issue:<number>"` first |
| Assumed issue was up-to-date | Requirements had changed in comments | Read most recent comments for latest requirements |
| Used `gh issue view` without `--comments` | Missed implementation notes from prior attempts | Always use `--comments` flag |

## Error Handling

| Problem | Solution |
|---------|----------|
| Issue not found | Check issue number, may be in different repo |
| No comments | Issue may be new or have minimal discussion |
| Auth error | Run `gh auth status` to verify |
| Rate limited | Wait or use authenticated requests |

## Best Practices

1. **Always read comments first** - They contain implementation history
2. **Check for linked PRs** - Prior attempts may exist
3. **Note acceptance criteria** - Success criteria should be clear
4. **Look for blockers** - Dependencies may not be resolved
5. **Extract key decisions** - Design choices should inform implementation

## References

- See gh-post-issue-update for posting progress updates
- GitHub CLI docs: https://cli.github.com/manual/gh_issue_view
