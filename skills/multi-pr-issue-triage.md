---
name: multi-pr-issue-triage
description: Triage a backlog of open GitHub issues, close resolved ones with comments,
  and implement remaining issues as ordered PRs with dependency management. Use when
  facing a batch of open issues that need classification and implementation.
category: testing
date: '2026-03-19'
version: 1.0.0
tags:
- github
- pr-workflow
- issue-triage
- bats
- graphql
- shell-testing
---
# Multi-PR Issue Triage Workflow

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-02-25 |
| Objective | Resolve 9 open GitHub issues across preflight check and pip-audit feature areas |
| Outcome | 3 issues closed with comments, 5 PRs created (all merged or pending CI) |
| Session | ProjectScylla preflight_check.sh hardening + pip-audit integration |

## When to Use

- Facing a backlog of related GitHub issues with mixed resolution status
- Some issues are already resolved by merged PRs (need just a close comment)
- Some issues are interdependent (PR order matters)
- Need to implement multiple PRs efficiently with parallel work where possible

## Verified Workflow

### Phase 1: Triage — Close No-Code Issues First

```bash
# Pattern: informational close
gh issue comment <N> --body "$(cat <<'EOF'
## Closing: <reason>

<explanation of why no code needed>

**Decision**: No code changes needed. Closing as <reason>.
EOF
)"
gh issue close <N> --reason "completed"   # for already-fixed
gh issue close <N> --reason "not planned" # for not-applicable
```

Close these immediately so the issue count is accurate for planning.

### Phase 2: Dependency Analysis

Map issues into a DAG:
- Independent issues → can run in parallel
- Dependent issues → must wait for predecessor PR to merge

Example:
```
PR1 (#909) ──┐
PR5 (#983) ──┤── independent, run in parallel
PR2 (#918) ──┘

PR3 (#913/#914) ──── depends on PR2 (script location)
PR4 (#915) ──────── depends on PR3 (final behavior)
```

### Phase 3: Parallel Implementation

Launch independent PRs as background agents:
```
Task(PR1, run_in_background=True)
Task(PR2, run_in_background=True)
Task(PR5, run_in_background=True)
```

**WARNING**: Background agents on the same repo fight over the working tree branch.
Use `isolation: "worktree"` parameter when launching agents so each gets its own
isolated git worktree. Without this, agents switching branches will block each other.

### Phase 4: Sequential Implementation for Dependent PRs

```bash
# Branch dependent PR off predecessor's local branch (not main)
# This lets you work before the predecessor merges
git checkout -b 913-914-feature predecessor-branch

# After predecessor merges, rebase onto updated main
git fetch origin main
git rebase origin/main
```

### Phase 5: Verify and Push

```bash
# Always run tests before committing
pixi run test-shell   # for BATS tests
pixi run python -m pytest tests/unit/... -v  # for Python tests

# Push and create PR with auto-merge
git push -u origin <branch>
gh pr create --title "..." --body "Closes #N"
gh pr merge <PR> --auto --rebase
```

## Key Technical Patterns

### Bash `:-` vs `-` Operator (Shell Mock Trap)

When a test needs to pass empty string as a meaningful sentinel value:

```bash
# WRONG: empty string falls through to default
_val="${MY_VAR:-$_DEFAULT}"

# CORRECT: only substitutes when truly unset
_val="${MY_VAR-$_DEFAULT}"

# Then add explicit empty-check guard
if [[ -n "$_val" ]]; then
    _json="{\"field\":${_val}}"
else
    _json="{\"field\":null}"   # or [] for arrays
fi
```

**Symptom**: `MY_VAR=""` produces malformed JSON like `{"number":}` instead of `{}`

### GraphQL vs REST for PR-to-Issue Linking

REST N+1 (avoid for large repos):
```bash
gh pr list --state all --json number,title,state --limit 100  # misses older PRs
gh pr view <N> --json closingIssuesReferences                  # one call per PR
```

GraphQL (single call, all PRs):
```bash
gh api graphql \
  -f "query=$(cat <<'GRAPHQL'
query($q:String!){search(query:$q,type:ISSUE,first:100){nodes{...on PullRequest{
  number,title,state,closingIssuesReferences(first:25){nodes{number}}
}}}}
GRAPHQL
)" \
  -f "q=repo:OWNER/REPO is:pr ISSUE_NUMBER"
```

Note: ShellCheck SC2016 will flag `$q` in single-quoted GraphQL strings. Add:
```bash
# shellcheck disable=SC2016  # $q is a GraphQL variable, not a shell variable
```

Always add REST fallback:
```bash
if [[ -n "$REPO_FULL" ]] && _graphql_check3 "$REPO_FULL" "$ISSUE"; then
    : # GraphQL succeeded
else
    _rest_check3 "$ISSUE"
fi
```

### Guarded BATS Integration Tests

```bash
setup_file() {
    if [[ "${PREFLIGHT_INTEGRATION:-0}" != "1" ]]; then
        skip "Set PREFLIGHT_INTEGRATION=1 to run integration tests"
    fi
    if ! gh auth status >/dev/null 2>&1; then
        skip "gh is not authenticated — run 'gh auth login' first"
    fi
}
```

CI workflow explicitly disables:
```yaml
- name: Run shell tests
  run: pixi run test-shell
  env:
    PREFLIGHT_INTEGRATION: "0"
```

Tests appear as `ok N ... # skip ...` in normal BATS output (not failures).

## Failed Attempts

### Background Agent Worktree Conflict

**What happened**: Launched PR1, PR2, and PR5 agents simultaneously as background tasks. The PR5 agent switched the main working tree to branch `983-pip-audit-precommit`. When the PR2 agent tried to switch to its branch, it was blocked and returned:
> "Please run `git -C ... switch 918-consolidate-preflight-location` manually"

**Root cause**: Multiple agents sharing the same git working tree fight over the current branch. Only one branch can be checked out at a time.

**Fix applied**: Implemented PR2 manually after PR5 agent completed.

**Prevention**: Use `isolation: "worktree"` parameter in Task tool so each agent gets its own isolated git worktree:
```python
Task(
    description="PR2 implementation",
    subagent_type="Bash",
    prompt="...",
    isolation="worktree",  # prevents branch conflicts
    run_in_background=True
)
```

## Results

| PR | Issue(s) | Key Change | Tests |
|----|----------|------------|-------|
| #1093 | #909 | Fix `:-` to `-` in mock + BATS tests 9-10 | 10/10 pass |
| #1094 | #983 | pip-audit pre-commit hook + 24 unit tests | 24/24 pass |
| #1095 | #918 | Move script to `scripts/`, update 4 references | 10/10 pass |
| #1096 | #913, #914 | GraphQL replaces O(N) REST, REST fallback | 10/10 pass |
| #1097 | #915 | Guarded integration tests, CI env var guard | 10+2 skip |

## References

- [BATS documentation](https://bats-core.readthedocs.io/en/stable/)
- [GitHub GraphQL API](https://docs.github.com/en/graphql)
- [ShellCheck SC2016](https://www.shellcheck.net/wiki/SC2016)
- ProjectScylla PRs: #1093, #1094, #1095, #1096, #1097
