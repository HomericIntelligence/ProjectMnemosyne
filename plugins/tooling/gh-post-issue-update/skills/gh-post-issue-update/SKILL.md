---
name: gh-post-issue-update
description: "Post structured updates to GitHub issues for progress tracking"
category: tooling
source: ProjectOdyssey
date: 2025-12-30
---

# Post Issue Update

Post implementation notes, status updates, and findings to GitHub issues.

## Overview

| Date | Objective | Outcome |
|------|-----------|---------|
| 2025-12-30 | Structured progress reporting on issues | Clear audit trail of work done |

## When to Use

- (1) Reporting implementation progress
- (2) Documenting design decisions
- (3) Posting completion summaries
- (4) Sharing findings or blockers

## Verified Workflow

1. **Identify update type**: Progress, completion, decision, or blocker
2. **Structure content**: Use appropriate template
3. **Post update**: Use `gh issue comment` with heredoc
4. **Verify posted**: Check issue on GitHub

## Results

Copy-paste ready commands:

```bash
# Short status update
gh issue comment <number> --body "Status: [brief update]"

# Detailed notes with heredoc
gh issue comment <number> --body "$(cat <<'EOF'
## Implementation Notes

Content here...
EOF
)"

# From file (for complex content)
gh issue comment <number> --body-file /path/to/file.md
```

### Progress Update Template

```bash
gh issue comment <number> --body "$(cat <<'EOF'
## Progress Update

### Completed
- [x] Created module structure
- [x] Implemented core functions

### In Progress
- [ ] Writing unit tests

### Next Steps
1. Complete test coverage
2. Integration testing
EOF
)"
```

### Implementation Complete Template

```bash
gh issue comment <number> --body "$(cat <<'EOF'
## Implementation Complete

**PR**: #<pr-number>

### Summary
[Brief description of what was implemented]

### Files Changed
- `path/to/file1.mojo` - Added tensor operations
- `path/to/file2.mojo` - Updated imports

### Testing
- All 15 tests pass
- Coverage: 85%

### Verification
- [x] Tests pass
- [x] Pre-commit passes
- [x] Manual verification complete
EOF
)"
```

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|------------|--------|
| Used double quotes in heredoc | Variables expanded unexpectedly, broke formatting | Use `<<'EOF'` (quoted) to prevent variable expansion |
| Posted very long single comment | Hard to read, hit character limits | Split into multiple focused comments |
| Didn't use markdown formatting | Wall of text, hard to parse | Use headers, lists, and code blocks |
| Posted update without PR link | Reviewers couldn't find the code | Always include PR number when work is complete |

## Error Handling

| Problem | Solution |
|---------|----------|
| Issue locked | Contact maintainer or use PR comments |
| Rate limited | Wait and retry |
| Auth error | Run `gh auth status` |
| Content too long | Split into multiple comments |

## Best Practices

1. **Be Concise**: Focus on actionable information
2. **Use Structure**: Headers and lists improve readability
3. **Include Context**: Future readers need to understand decisions
4. **Link Related Items**: Reference PRs, other issues, commits
5. **Update Regularly**: Don't wait until completion

## References

- See gh-read-issue-context for reading issue context first
- GitHub CLI docs: https://cli.github.com/manual/gh_issue_comment
