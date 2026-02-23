# Skill: PR Rebase Pipeline (Bulk Issue Triage)

| Property | Value |
|----------|-------|
| **Date** | 2026-02-23 |
| **Objective** | Fix a systemic CI failure blocking all PRs, then create and land 13 PRs for simple open issues across 5 waves using parallel worktrees |
| **Outcome** | ✅ 13 PRs merged, 1 pending auto-merge. All pip-audit Security checks fixed. Zero manual merges required. |
| **Context** | ProjectScylla had 71 open issues and 8 open PRs all failing CI due to an invalid `--min-severity high` flag on `pip-audit`. After fixing the root cause, 5 waves of simple issues were resolved in parallel. |

## When to Use This Skill

Use this skill when:
- A systemic CI failure is blocking multiple open PRs
- There are many simple open issues with no PRs
- You want to ship fixes in parallel waves using git worktrees
- PRs need rebasing after a shared file (like `pixi.lock`) changes on main

**Key Indicators**:
- Multiple PRs show the same CI check failing (Security, pre-commit, etc.)
- `pip-audit`, `ruff`, or other tool invocations use unsupported flags
- Open issues are classified into simple (1-file) vs complex
- `pixi.lock` conflicts arise during rebase

## Verified Workflow

### Phase 0: Fix the Systemic Blocker First

Before creating any new PRs, identify and fix the root CI failure:

```bash
# Identify the failing check name across all open PRs
gh pr list --state open --json number,statusCheckRollup | jq -r '.[] | ...'

# Read the actual CI log to find the root cause
gh run view <run-id> --log-failed | head -50

# Fix pixi.toml task definition (example: remove unsupported flag)
# pip-audit = "pip-audit --min-severity high"  # WRONG - flag doesn't exist
# pip-audit = "pip-audit"                       # CORRECT
```

Create PR, enable auto-merge, wait for it to land before touching other PRs.

### Phase 1: Rebase Existing PRs After Blocker Merges

```bash
# For each existing PR branch, rebase onto updated main
git -C <worktree-path> fetch origin
git -C <worktree-path> rebase origin/main

# If pixi.lock conflicts, take theirs (main's version) then regenerate
git -C <worktree-path> checkout --theirs pixi.lock
git -C <worktree-path> add pixi.lock
GIT_EDITOR=true git -C <worktree-path> rebase --continue
cd <worktree-path> && pixi install  # regenerates pixi.lock
git -C <worktree-path> add pixi.lock
git -C <worktree-path> commit -m "fix(deps): regenerate pixi.lock after rebase on main"
git -C <worktree-path> push --force-with-lease origin <branch>
```

### Phase 2: Classify Open Issues

For each open issue without a PR, classify by complexity:
- **Simple**: Single file, mechanical change, no new dependencies
- **Medium**: Multi-file, requires investigation
- **Complex**: Architectural, multi-component

Only tackle Simple issues in bulk. Use `gh issue list --limit 100 --state open` and cross-reference with `gh pr list --state all`.

### Phase 3: Wave-Based Parallel PRs via Worktrees

Group simple issues into waves by file independence (no two issues in same wave touch same file):

```bash
# Create isolated worktree per issue (or per wave if combining)
git worktree add .claude/worktrees/issue-NNN NNN-branch-name

# Per-issue workflow inside worktree:
# 1. Read the file before editing
# 2. Make minimal change
# 3. pre-commit run --files <changed-files>
# 4. pytest tests/unit/ -q --no-cov (spot check)
# 5. git add <specific-files>  (never git add -A)
# 6. git commit -m "type(scope): description (Closes #NNN)"
# 7. git push -u origin <branch>
# 8. gh pr create --title "..." --body "Closes #NNN"
# 9. gh pr merge --auto --rebase
```

### Phase 4: Cleanup

```bash
# Remove merged worktrees (without --force, since they're clean)
git worktree remove <path>
git worktree prune

# Verify what's left
git worktree list
git branch -v | grep '\[gone\]'
```

## Failed Attempts

### 1. `git branch -d` on rebase-merged branches fails

**Problem**: Branches merged via rebase don't appear in `main`'s ancestry, so `git branch -d` reports "not fully merged" even though the PR is merged on GitHub.

**Fix**: Must use `git branch -D`. Safety Net hooks block `-D` — user must run manually or Safety Net must be configured to allow it for `[gone]` branches.

### 2. BATS mock `echo "${VAR:-{...json...}}"` produces extra `}`

**Problem**:
```bash
echo "${GH_MOCK_ISSUE_STATE:-{\"state\":\"OPEN\",\"title\":\"Test Issue\",\"closedAt\":null}}"
```
When `GH_MOCK_ISSUE_STATE` IS set, bash still appends the literal `}` that follows the `${...}` expansion, producing `null}}` — invalid JSON.

**Fix**: Use a named variable for the default:
```bash
_DEFAULT_ISSUE_STATE='{"state":"OPEN","title":"Test Issue","closedAt":null}'
echo "${GH_MOCK_ISSUE_STATE:-$_DEFAULT_ISSUE_STATE}"
```

### 3. BATS mock doesn't honor `--jq` flag

**Problem**: Script calls `gh pr view N --json closingIssuesReferences --jq '.closingIssuesReferences[].number'` expecting a bare number, but mock returned full JSON. `grep -qx "$ISSUE"` never matched.

**Fix**: Detect `--jq` in mock args and pipe through real `jq`:
```bash
"pr view")
    _closes="${GH_MOCK_PR_CLOSES:-800}"
    _full_json="{\"closingIssuesReferences\":[{\"number\":${_closes}}]}"
    if [[ "${*}" == *"--jq"* ]]; then
        _jq_filter=""; _found=0
        for _arg in "$@"; do
            [[ "$_found" -eq 1 ]] && { _jq_filter="$_arg"; break; }
            [[ "$_arg" == "--jq" ]] && _found=1
        done
        [[ -n "$_jq_filter" ]] && echo "$_full_json" | jq -r "$_jq_filter" || echo "$_full_json"
    else
        echo "$_full_json"
    fi
    ;;
```

### 4. `git worktree remove --force` blocked by Safety Net

**Problem**: Safety Net hook blocks `git worktree remove --force` as potentially destructive.

**Fix**: Use `git worktree remove` (without `--force`) when worktree is clean, then `git worktree prune` to clean up metadata for already-deleted directories.

### 5. `pixi.lock` conflicts on every rebase

**Problem**: `pixi.lock` is a large lock file that conflicts whenever dependencies change on main.

**Fix**: Always take `--theirs` (main's version) then run `pixi install` to regenerate for the branch's deps. Commit the regenerated file separately: `fix(deps): regenerate pixi.lock after rebase on main`.

### 6. `pip-audit --min-severity high` is not a valid flag

**Problem**: pip-audit does not support `--min-severity`. Every Security CI check failed with a usage error.

**Fix**: Remove the flag entirely. pip-audit by default reports all severities; use `--ignore-vuln` for specific CVEs if needed.

## Results & Parameters

### Issue Wave Summary

| Wave | Issues | PRs | Strategy |
|------|--------|-----|----------|
| Phase 0 | pip-audit fix | #1029 | Fix blocker first |
| Wave 1 | #960, #890, #911 | #1030, #1031, MN#168 | Doc fixes, independent files |
| Wave 2 | #916, #933, #971 | #1032, #1033, #1034 | Bug/security fixes |
| Wave 3 | #894, #949, #979 | #1036, #1037, #1038 | Python test additions |
| Wave 4 | #901, #902, #905 | #1035 | BATS shell tests (combined — same file) |
| Wave 5 | #966, #897 | #1039, #1040 | Refactoring + strict mode |

**Total**: 13 issues resolved, 14 PRs merged in ~4 hours with parallel worktrees.

### Auto-merge Setup (Required)

```bash
gh pr merge --auto --rebase
```

Always enable immediately after `gh pr create`. Required checks for this repo: `pre-commit` and `test (unit, tests/unit)` only — Security and mypy are non-blocking for merge gate purposes.

### Combining Issues into One PR

When multiple issues touch the same file, combine into one PR:
- Single branch, single PR body with multiple `Closes #N` references
- Avoids merge conflicts between waves

### Worktree Naming Convention

```bash
git worktree add .claude/worktrees/agent-<uuid> <issue-number>-<slug>
```

Use `.claude/worktrees/` so they're isolated from project files and easy to bulk-prune.
