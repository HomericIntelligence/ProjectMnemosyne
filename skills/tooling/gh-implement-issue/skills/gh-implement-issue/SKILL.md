---
name: gh-implement-issue
description: "End-to-end implementation workflow for a GitHub issue from planning through PR creation. Use when starting work on an issue from scratch."
category: github
---

# Implement GitHub Issue

## Overview

| Item | Details |
|------|---------|
| Date | N/A |
| Objective | Complete workflow for implementing a GitHub issue from start to finish. - Starting work on a new issue |
| Outcome | Operational |


Complete workflow for implementing a GitHub issue from start to finish.

## When to Use

- Starting work on a new issue
- Need structured workflow from branch to PR
- Want to follow best practices end-to-end
- Working on assigned GitHub issue

## Quick Reference

> **Note:** `<skill-dir>` is the absolute path to this skill's directory.
> Resolve it with: `SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"`
> or use the skill's installed path directly.

```bash
# 0. Pre-flight check (REQUIRED - runs all 6 checks automatically)
# Replace <skill-dir> with the absolute path to this skill directory
bash <skill-dir>/scripts/preflight_check.sh <issue>

# 1. Fetch issue and create branch (only after pre-flight passes)
gh issue view <issue>
git checkout -b <issue>-<description>

# 2. Implement with TDD
# - Write tests first
# - Implement code
# - Run tests: mojo test tests/

# 3. Quality checks
just pre-commit-all

# 4. Commit and PR
git add . && git commit -m "feat: description

Closes #<issue>"
git push -u origin <branch>
gh pr create --issue <issue>
```

## Pre-Flight Check Results

| Result | Check | Behavior |
|--------|-------|----------|
| STOP (exit 1) | Issue is CLOSED | Halt immediately — work may be done |
| STOP (exit 1) | PR is MERGED | Halt immediately — duplicate work risk |
| STOP (exit 1) | Worktree conflict | Halt — branch already checked out |
| WARN (exit 0) | Existing commits | Proceed with caution — may be partial work |
| WARN (exit 0) | Open PR exists | Proceed with caution — coordinate with author |
| WARN (exit 0) | Existing branch | Proceed with caution — review before creating new branch |
| PASS (exit 0) | All clear | Safe to proceed |

## Verified Workflow

1. **Run pre-flight check**: `bash <skill-dir>/scripts/preflight_check.sh <issue>` — automatically runs all 6 checks; stops on critical failures
2. **Read issue context**: `gh issue view <issue> --comments` - understand requirements, prior context
3. **Create branch**: `git checkout -b <issue>-<description>`
4. **Post start comment**: Document approach on the issue
5. **Write tests first**: TDD approach - tests drive implementation
6. **Implement code**: Build functionality to pass tests
7. **Quality check**: Format code and run pre-commit
8. **Commit**: Create focused commit with issue reference
9. **Push and PR**: Create PR linked to issue
10. **Post completion**: Document summary on the issue
11. **Monitor CI**: Verify all checks pass

## Branch Naming Convention

Format: `<issue-number>-<description>`

Examples:

- `42-add-tensor-ops`
- `73-fix-memory-leak`
- `105-update-docs`

## Commit Message Format

Follow conventional commits:

```text
type(scope): Brief description

Detailed explanation of changes.

Closes #<issue-number>
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

## Code Quality Checklist

Before creating PR:

- [ ] Issue requirements met
- [ ] Tests written and passing
- [ ] Code formatted (pixi run mojo format)
- [ ] Pre-commit hooks pass
- [ ] No warnings or unused variables
- [ ] Documentation updated
- [ ] Commit messages follow convention

## Error Handling

| Problem | Solution |
|---------|----------|
| Pre-flight: issue CLOSED | Stop work; issue already resolved |
| Pre-flight: merged PR found | Stop work; check PR for implementation |
| Pre-flight: worktree conflict | Navigate to existing worktree or remove it |
| Pre-flight: warns existing branch | Review branch before creating new one |
| Issue not found | Verify issue number |
| Branch exists | Use different name or delete old branch |
| Tests fail | Fix code before creating PR |
| CI fails | Address issues before merge |

## Documentation Requirements

Post documentation directly to the GitHub issue:

```bash
# Post implementation started
gh issue comment <issue> --body "$(cat <<'EOF'
## Implementation Started

**Branch**: `<branch-name>`

### Approach
[Brief description of implementation approach]

### Files to Modify
- `path/to/file1.mojo`
- `path/to/file2.mojo`
EOF
)"

# Post completion summary
gh issue comment <issue> --body "$(cat <<'EOF'
## Implementation Complete

**PR**: #<pr-number>

### Summary
[What was implemented]

### Verification
- [x] Tests pass
- [x] Pre-commit passes
EOF
)"
```

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|------------|--------|
| N/A | This skill was migrated from uncategorized | Document failures as they occur |


## Results & Parameters

N/A — this skill describes a workflow pattern.

## References

- See CLAUDE.md for complete development workflow
- See CLAUDE.md for Mojo syntax standards
- See CLAUDE.md for zero-warnings policy
- See `issue-preflight-check` skill for full pre-flight check documentation
