---
name: issue-validation-workflow
description: "Validate GitHub issue state against codebase reality before implementation. Use when starting work on multiple issues to prevent wasted effort on already-resolved issues."
category: evaluation
date: 2026-02-12
---

# Issue Validation Workflow

Systematically validate GitHub issue state against codebase reality before starting implementation work.

## Overview

| Date | Objective | Outcome |
|------|-----------|---------|
| 2026-02-12 | Validate 12 GitHub issues (340, 341, 342, 346, 419-426) before parallel implementation | Discovered 6/12 issues already resolved, 1 issue scope inverted, triaged remaining into parallel workstreams |

## When to Use

Use this workflow when:
- (1) Starting work on multiple GitHub issues simultaneously
- (2) Issues were filed weeks/months ago and may be stale
- (3) You want to avoid duplicate work
- (4) Triaging a batch of issues for parallel implementation
- (5) **Before invoking /advise** to search for relevant skills

## Verified Workflow

### Phase 1: Issue Discovery

```bash
# Fetch all issues in bulk
for issue in 340 341 342 346 419 420 421 422 423 424 425 426; do
    gh issue view $issue --json title,body,labels,state --repo <repo>
done
```

### Phase 2: Parallel Codebase Exploration

Launch **parallel explore agents** to verify issue claims against codebase reality:

```
Task tool with subagent_type=Explore (2-3 parallel agents recommended)
```

**Agent 1 - Docker/Config Issues (340, 341, 342, 422, 423)**:
- Verify missing modules exist/don't exist
- Check Docker README state
- Verify workflow files
- Check pixi.toml and .pre-commit-config.yaml

**Agent 2 - Test Coverage Issues (419, 420, 421)**:
- Check if test files already exist
- Count lines of existing tests vs source
- Identify actual coverage gaps

**Agent 3 - Dead Code Issues (424, 425, 426)**:
- Grep for methods/constants claimed to exist
- Verify they're actually unused
- Check if requirements are in CLAUDE.md

### Phase 3: Evidence-Based Triage

For each issue, categorize:

| Category | Action | Example |
|----------|--------|---------|
| **Already Resolved** | Close with evidence | Issue #419: `tests/unit/core/test_results.py` exists (292 lines) |
| **Scope Inverted** | Update issue description | Issue #426: Remove "Python justification" lines (not add them) |
| **Split Required** | Break into sub-issues | Issue #421: Split into 8 module-specific PRs |
| **Valid** | Proceed with implementation | Issue #340: Create missing scylla.judge.runner |

### Phase 4: Use /advise After Validation

**CRITICAL**: Only invoke `/advise` **after** validating issues:

```
/advise <validated objective>
```

Example:
```
/advise Implement GitHub issues 340, 341, 342, 346, 421 in parallel using worktrees
```

**Why**: `/advise` searches the skills marketplace for relevant patterns. Searching with stale/incorrect issue descriptions wastes time.

### Phase 5: Close Resolved Issues

```bash
# Close each resolved issue with evidence
gh issue close 419 --comment "Closing as already resolved. Evidence: \
tests/unit/core/test_results.py exists with 292 lines and 26 comprehensive tests. \
Coverage for scylla/core/results.py is complete."

gh issue close 420 --comment "Closing as already resolved. Evidence: \
All 3 test files exist under tests/unit/discovery/: \
- test_agents.py (398 lines, 20+ tests) \
- test_skills.py (408 lines, 25+ tests) \
- test_blocks.py (399 lines, 25+ tests) \
Total: ~1200 lines of comprehensive test coverage."
```

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|------------|--------|
| Trusted issue descriptions without verification | 6/12 issues were already resolved but still open | Always verify issue state against codebase - issues go stale |
| Single sequential exploration | Took too long to verify 12 issues | Use parallel explore agents (2-3) grouped by domain |
| Used /advise before validation | Skills returned were irrelevant to actual work needed | Validate issues FIRST, then search skills marketplace |
| Assumed issue requirements were accurate | Issue #426 referenced non-existent CLAUDE.md rules | Grep for requirements in docs - don't assume |

## Results & Parameters

### Session Metrics

| Metric | Value |
|--------|-------|
| Issues reviewed | 12 |
| Issues already resolved | 6 (50%) |
| Issues with inverted scope | 1 |
| Issues requiring split | 1 (into 8 sub-PRs) |
| Valid issues needing work | 5 |
| Time saved by validation | ~6 duplicate implementations avoided |

### Optimal Parallel Agent Configuration

**2-3 Explore agents** grouped by:
- Domain similarity (e.g., Docker issues together)
- Complexity (simple file checks vs deep code analysis)

```
Agent 1: Docker/Config (4-5 issues)
Agent 2: Test Coverage (3-4 issues)
Agent 3: Code Cleanup (2-3 issues)
```

### Evidence Collection Template

For "already resolved" issues:
```
Issue #XXX: <title>
Status: Already resolved
Evidence:
- File: <path>
- Lines: <count>
- Content: <brief summary>
- Verification: <grep/ls command>
```

For "scope inverted" issues:
```
Issue #XXX: <title>
Status: Scope inverted
Current requirement: <what issue says>
Actual requirement: <what codebase shows>
Evidence: <grep/file content>
```

## Integration with Other Skills

This skill **must run before**:
- `/advise` - Search skills marketplace with validated objectives
- `parallel-issue-implementation` - Implement validated issues in parallel
- `git-worktree-workflow` - Create worktrees only for valid issues

This skill **builds on**:
- `gh-read-issue-context` - Read issue body and comments
- Explore agents - Parallel codebase exploration

## Success Criteria

- [ ] All issues verified against codebase state
- [ ] Evidence collected for "already resolved" claims
- [ ] Stale issues closed with explanatory comments
- [ ] Scope-inverted issues updated or noted
- [ ] Large issues triaged into sub-tasks
- [ ] Only validated issues proceed to implementation

## References

- Session: 2026-02-12 - Validated issues 340, 341, 342, 346, 419-426
- Repository: ProjectScylla
- Command: `/advise Lets work on github issues 340, 341, 342, 346, and 419 through 426`
