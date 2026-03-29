---
name: batch-pr-ci-fix-workflow
description: "Use when: (1) multiple PRs have failing CI checks (formatting, pre-commit, broken links, broken JSON, mypy), (2) a common CI failure pattern affects many PRs and needs a root-cause fix before rebasing, (3) PRs need batch auto-merge after fixes, (4) JSON files are bulk-corrupted and must be repaired before merging, (5) identifying required vs non-required checks, (6) recovering auto-merge after force-push, (7) reconstructing a branch that conflicts with a src-layout migration."
category: ci-cd
date: 2026-03-29
version: "2.0.0"
user-invocable: false
verification: verified-ci
tags: []
---
# Batch PR CI Fix Workflow

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-29 |
| **Objective** | Diagnose and fix CI failures across multiple open PRs — formatting, pre-commit hooks, broken JSON, MkDocs link errors, rebase-based fixes, required vs non-required checks, src-layout migration conflicts |
| **Outcome** | Consolidated from 6 source skills (v1.0.0) + new learnings from ProjectScylla PRs #1739/#1734/#1737/#1740 (v2.0.0) |

## When to Use

- Multiple open PRs have failing CI checks (formatting, pre-commit, broken links, mypy, JSON validation)
- A common CI failure pattern affects many PRs and needs a root-cause fix on `main` first
- PRs have CONFLICTING/DIRTY merge state from being behind main (merge conflicts block CI from running)
- A batch edit corrupted JSON files across many plugin files
- You need to enable auto-merge across 20+ open PRs at once
- A PR CI failure is caused by branch staleness (crashes unrelated to the PR's own changes)
- **[NEW v2.0.0]** You need to distinguish required (blocking) checks from non-required (advisory) checks
- **[NEW v2.0.0]** Auto-merge was cleared by a force-push and must be re-enabled
- **[NEW v2.0.0]** A branch conflicts with a src-layout migration and standard rebase fails immediately
- **[NEW v2.0.0]** Pre-existing failures look like blockers but are not required checks

## Verified Workflow

### Quick Reference

```bash
# 1. Assess open PRs and CI status
gh pr list --state open --json number,title,headRefName --limit 100
gh pr checks <pr-number>
gh pr checks <pr-number> 2>&1 | grep -E "(fail|pending)"

# 2. Get failure logs
gh run view <run-id> --log-failed | head -100

# 3. Fix each PR (pick appropriate fix path below)

# 4. Enable auto-merge
gh pr merge <pr-number> --auto --rebase

# 5. Monitor
gh pr view <pr-number> --json state,mergedAt
```

### Phase 0: Triage Before Touching Anything

```bash
# Check status of all open PRs
gh pr list --state open
gh pr checks <number>

# For each failing PR, read the CI log
gh run view <run-id> --log-failed | head -60

# Check if branch is behind main (causes merge conflicts → CI won't even run)
gh pr view <number> --json mergeable,mergeStateStatus
# "CONFLICTING" → rebase needed before CI can trigger
```

The hook name in the CI log tells you which fix path to take:

| Hook / Error | Fix Path |
|------|----------|
| `Ruff Format Python` | Auto-fix (blank lines, indentation) |
| `Markdown Lint` | Auto-fix (MD032 blank lines) |
| `Check Tier Label Consistency` | Manual doc fixes (see self-catch path below) |
| `mojo-format` | Run `pixi run mojo format <file>` or read CI diff |
| `validate-test-coverage` | Add missing test file to CI workflow patterns |
| `ruff-check-python` | Fix unused imports/variables |
| Broken markdown links (MkDocs strict) | Remove or fix link |
| Invalid JSON | Use Python json module fix (see bulk JSON path) |
| `bats` (command not found) | Pre-existing on main — NOT a required check, ignore |
| `docker-build-timing` (Trivy CVEs) | Pre-existing on main — NOT a required check, ignore |

### Phase 0.5: [NEW v2.0.0] Identify Required vs Non-Required Checks

Not all failing checks block a PR merge. Required checks are configured in GitHub branch protection
rules. Non-required checks may fail without preventing auto-merge.

```bash
# See which checks are required (branch protection rules)
gh api repos/{owner}/{repo}/branches/main --jq '.protection.required_status_checks.contexts[]'

# Alternative: check PR status with context
gh pr checks <pr-number> 2>&1
# Required checks show as blocking; non-required appear in CI but don't gate merge

# Confirm a failure is pre-existing on main (not introduced by this PR)
gh run list --branch main --status failure --limit 5
gh run view <main-run-id> --log-failed | grep "<check-name>"
```

**Decision rule**: If a check fails on `main` too and is NOT in the required_status_checks list,
treat it as advisory-only. Never spend time fixing advisory failures when required checks pass.

**Known pre-existing non-required failures in ProjectScylla** (as of 2026-03-29):
- `bats` — `fail: command not found` — bats test runner not installed in CI environment
- `docker-build-timing` — Trivy CVE scanner reports known CVEs — not a required gate

**When in doubt**: Enable auto-merge and let GitHub report whether it can proceed. If auto-merge
reports "Waiting for required checks", those are the blocking ones.

### Phase 1: Fix Root Cause on Main First (When a Common Pattern Exists)

If many PRs all fail with the same format error:

```bash
# Find which file fails format on any PR
gh run view <run_id> --log-failed 2>&1 | grep "reformatted"

# Check the file's long lines (code limit = 88 chars, markdown = 120 chars)
awk 'length > 88 {print NR": "length": "$0}' <file> | head -20
```

1. Create branch from main, fix the formatting/API issue
2. Push, create PR, enable auto-merge: `gh pr merge --auto --rebase`
3. Wait for it to merge, then mass-rebase all PRs (see `batch-pr-rebase-conflict-resolution-workflow`)

### Phase 2: Fix Trivial Formatting Failures (ruff-format, markdownlint)

```bash
git checkout <branch>
git pull origin <branch>

# Let the hook auto-fix
pre-commit run --all-files

# Check what changed
git status --short

# Stage only the changed files
git add <changed-files>
git commit -m "fix(tests): add missing blank line between test classes"
git push origin <branch>
```

**Key**: always `git status --short` after pre-commit to know what was auto-fixed before staging.

**ruff-format after identifier rename**: When a rename shortens variable/function names, multi-line
expressions may now fit on one line. ruff-format will collapse them. Run:

```bash
# Targeted ruff-format only (faster than --all-files when only formatting changed)
pre-commit run ruff-format-python --all-files
git add -u
git commit -m "fix(format): apply ruff format after identifier rename"
git push origin <branch>
```

**Test assertion renames**: When an identifier is renamed (e.g., `Retrospective` → `Learn`), search
for string literals in test files — they are NOT auto-updated by rename refactoring:

```bash
# Find old strings in test files
grep -r "OldName" tests/
# Fix each assertion manually, then run pre-commit to catch any formatting cascade
```

### Phase 3: Fix "Self-Catch" Expanded-Scope Pre-commit Hook

When a PR widens a pre-commit hook (e.g., from checking one file to scanning `*.md`) and the wider
scan catches pre-existing violations in other files the PR didn't touch:

**Step 1**: Reproduce the exact CI environment (exclude untracked local dirs):

```bash
# Wrong — includes local directories that don't exist in CI
pixi run python scripts/check_tier_label_consistency.py

# Correct — matches CI (exclude untracked local checkouts)
pixi run python scripts/check_tier_label_consistency.py --exclude ProjectMnemosyne
```

**Step 2**: Fix all violations and verify clean, then commit:

```bash
git add <all modified files>
git commit -m "docs: fix N tier label mismatches caught by expanded consistency checker"
git push origin <branch>
```

### Phase 4: Fix MkDocs Strict Mode Link Failures

MkDocs strict mode aborts on broken/unrecognized links:

| Error Type | Example | Fix |
|-----------|---------|-----|
| Link to non-existent file | `[Math](math.md)` when file doesn't exist | Remove link or create file |
| Cross-directory link | `[Workflow](../../.github/workflows/file.yml)` | Convert to backtick code reference |
| Unrecognized relative link | `[Examples](../../examples/)` | Use valid docs-relative path or remove |

```bash
# Switch to PR branch and find broken links
git checkout <branch-name>
gh run view <run-id> --log 2>&1 | grep -B5 "Aborted with.*warnings"

git add <file>
git commit -m "fix(docs): remove broken link to non-existent file"
git push origin <branch-name>
```

### Phase 5: Fix Branches Behind Main (Merge Conflicts)

If `mergeStateStatus == "CONFLICTING"`, CI won't trigger until the branch is rebased:

```bash
git checkout <branch>
git fetch origin main
git log --oneline HEAD..origin/main | wc -l  # How many commits behind?

git rebase origin/main
# For conflicted files where PR version should win:
git checkout --theirs <conflicted-file>
git add <conflicted-file>
git rebase --continue
```

**After rebase**: always re-run tests and pre-commit:

```bash
pre-commit run --all-files || true
git add -u && git commit -m "fix: apply pre-commit auto-fixes" || true
git push --force-with-lease origin <branch>
```

For `pixi.lock` conflicts:
```bash
git checkout --theirs pixi.lock
pixi install
git add pixi.lock
git rebase --continue
```

### Phase 5.5: [NEW v2.0.0] Recover Auto-Merge After Force-Push

After any `git push --force-with-lease` or `git push --force` (rebase, amend), GitHub clears
the auto-merge setting. This is **silent** — there is no notification.

```bash
# After force-push, always re-enable auto-merge
git push --force-with-lease origin <branch>
gh pr merge <pr-number> --auto --rebase

# Verify auto-merge is active
gh pr view <pr-number> --json autoMergeRequest
# Should show: {"autoMergeRequest": {"mergeMethod": "rebase", ...}}
# NOT: {"autoMergeRequest": null}
```

**Pattern**: force-push → auto-merge cleared → PR sits open indefinitely even after CI passes.
**Detection**: PR is green (all checks pass) but not merging. Check `--json autoMergeRequest`.
**Fix**: Always call `gh pr merge --auto --rebase` immediately after every force-push.

### Phase 6: Fix Pre-existing Staleness Crashes

When CI shows crashes in tests the PR never touched:

```bash
# Confirm failures are pre-existing (not PR-introduced)
gh run list --branch main --limit 5
gh pr diff <PR-number> --name-only  # PR-touched files

# Rebase onto current main
git rebase origin/main
git push --force-with-lease origin <branch-name>
```

**Key indicator**: if failing test files are NOT in the PR's changed files list, the failures are
pre-existing — always rebase before investigating code.

### Phase 7: Fix Bulk-Corrupted JSON Files

```bash
# Diagnose scope
python3 scripts/validate_plugins.py skills/ plugins/ 2>&1 | grep -c "Invalid JSON"
```

Use Python for safe, idempotent repair (NOT xargs/shell):

**Fix valid JSON (remove unwanted key):**
```python
import json, pathlib
for f in pathlib.Path('skills/').rglob('plugin.json'):
    try:
        data = json.loads(f.read_text())
        if 'tags' in data:
            del data['tags']
            f.write_text(json.dumps(data, indent=2) + '\n')
    except Exception:
        pass
```

**Fix trailing commas (regex):**
```python
import re
fixed_text = re.sub(r',(\s*[}\]])', r'\1', text)
```

```bash
# Verify then stage only modified tracked files
python3 scripts/validate_plugins.py skills/ plugins/ 2>&1 | tail -5
git add $(git diff --name-only)
```

### Phase 8: Enable Auto-Merge

```bash
gh pr merge <pr-number> --auto --rebase

# PRs reporting "Pull request is in clean status" → merge directly
gh pr merge --rebase <number>

# Batch enable auto-merge
for pr in <list>; do
  gh pr merge "$pr" --auto --rebase || echo "Failed: PR #$pr"
done
```

### Phase 9: [NEW v2.0.0] Handle src-Layout Migration Conflicts (Branch Reconstruction)

When a branch was forked **before** a src-layout migration (e.g., `scylla/` → `src/scylla/`),
standard rebase fails immediately with path conflicts on every file the PR touched.

**Detection signals:**
- Branch is 10+ commits behind main
- `mergeStateStatus == "CONFLICTING"` (DIRTY)
- CI shows only CodeQL/security checks — full CI suite didn't even run
- `git rebase origin/main` immediately conflicts on old paths that no longer exist

**Decision: Rebase vs Reconstruct**

```
Should I reconstruct instead of rebase?
├── Is branch 10+ commits behind main?           → +1 toward reconstruct
├── Did main undergo a src-layout/path migration? → +2 toward reconstruct
├── Does the PR delete entire module directories? → +1 toward reconstruct
├── Are there 5+ conflicted files on rebase?      → +1 toward reconstruct
└── Score >= 3 → Reconstruct from main
    Score < 3  → Attempt rebase with --theirs resolution
```

**Reconstruction workflow:**

```bash
# 1. Analyze the old PR's net effect
git log --oneline <old-branch>
git diff origin/main...<old-branch> --stat
git diff origin/main...<old-branch> --name-only --diff-filter=A  # added files
git diff origin/main...<old-branch> --name-only --diff-filter=D  # deleted files

# Read a file from the old branch using old paths
git show <old-branch>:<old-path/to/file.py>

# 2. Create a new branch from current main
git checkout -b feat/<description>-v2 origin/main

# 3. Apply the net effect as targeted edits (NOT cherry-pick of old commits)
#    Rewrite old paths to match new layout (e.g. scylla/ → src/scylla/)

# 4. Validate
pre-commit run --all-files
pytest tests/ -x -q

# 5. Create new PR, close old one
gh pr create --title "..." --body "..."
gh pr close <old-pr-number> --comment "Superseded by #<new-pr-number> — branch reconstructed from main after src-layout migration conflict."
```

**What to copy from the old branch**: Read each commit's diff carefully. Copy the *logical intent*,
not the patch. Old paths must be rewritten to match the new layout.

**Git auto-drops already-applied commits**: If some of the old PR's commits were already applied to
main, `git rebase` silently drops them (detects identical patch content even with different message).
This is expected — don't worry about "missing" commits that were already upstream.

### Phase 10: Verify

```bash
gh pr view <pr-number> --json state,mergedAt
gh pr list --state merged --limit 5 --json number,title,mergedAt
gh pr list --state open
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Run mojo format locally | `pixi run mojo format <file>` | GLIBC version mismatch on local machine | Can't run mojo format locally; use CI logs to identify what changed |
| `git checkout origin/$branch -b temp` | Single command to create tracking branch | Git syntax error | Use `git fetch origin $branch && git checkout -b temp origin/$branch` |
| Fixing link-check by editing unrelated files | Considered modifying CLAUDE.md | Failure was pre-existing on main | Verify if failure also exists on `main` before attempting a fix |
| Reproducing CI hook with local untracked dirs | Ran hook without `--exclude ProjectMnemosyne` | Local clone had dirs that don't exist in CI | Always exclude untracked directories that exist locally but not in CI |
| xargs/shell to fix bulk JSON | `xargs -I{} sh -c 'fix...'` | Safety Net blocks pattern | Use Python's `json` module for safe, idempotent JSON repair |
| `git add skills/` or `git add -A` after JSON fix | Staged untracked directories | Picks up nested untracked directories | Use `git add $(git diff --name-only)` |
| Run `gh pr merge --auto --squash` | Tried squash on rebase-only repo | Squash disabled | Test in order: `--squash` → `--merge` → `--rebase` |
| Investigate test code for pre-existing crash | Read crashing test files | Already fixed upstream | When failures are in untouched files and main passes them, rebase first |
| GraphQL PR status query | `gh pr list --json statusCheckRollup` | 504 Gateway Timeout under load | Fall back to per-PR `gh pr checks <number>` calls |
| Empty commit to trigger CI after rebase | Pushed empty commit | Validate workflow had path filter | Remove path filters from validate workflows |
| Standard rebase on post-migration branch | `git rebase origin/main` on stale branch | Immediate conflicts (old paths gone) | When branch pre-dates structural migration, reconstruct from main |
| Treating `bats`/`docker-build-timing` as blockers | Investigated Trivy CVEs and bats install | Both fail on main — not required checks | Verify a check fails on main before treating it as required |
| Not re-enabling auto-merge after force-push | Force-pushed, assumed auto-merge persisted | GitHub silently clears auto-merge on force-push | After every force-push: immediately run `gh pr merge --auto --rebase` |

## Results & Parameters

### Key Commands Reference

```bash
# List open PRs
gh pr list --state open --json number,title,headRefName

# Check CI status
gh pr checks <pr-number>
gh pr checks <pr-number> 2>&1 | grep -E "(fail|pending)"

# Get failure logs
gh run view <run-id> --log-failed

# Check if check is required
gh api repos/{owner}/{repo}/branches/main --jq '.protection.required_status_checks.contexts[]'

# Rebase and push
git fetch origin main && git rebase origin/main
git push --force-with-lease origin <branch-name>

# Enable auto-merge (ALWAYS do this after force-push too)
gh pr merge <pr-number> --auto --rebase

# Check auto-merge status
gh pr view <pr-number> --json autoMergeRequest

# Batch enable auto-merge
gh pr list --state open --json number --jq '.[].number' --limit 1000 | \
  while read pr; do gh pr merge "$pr" --auto --rebase || echo "Failed: PR #$pr"; done
```

### Required vs Non-Required Check Decision Tree

```
Is a check failing?
├── Does it also fail on main?
│   ├── YES → Is it in required_status_checks?
│   │         ├── YES → Must fix (rare — required check broken on main)
│   │         └── NO  → Advisory only; skip and proceed
│   └── NO  → PR introduced the failure; must fix
└── Is mergeStateStatus == "CONFLICTING"?
    └── YES → Full CI may not have run; rebase first, then re-evaluate
```

### Pre-commit Hook Reference

| Hook | Purpose | Common Fix |
|------|---------|------------|
| `Ruff Format Python` | Python formatting | 2 blank lines between top-level classes |
| `markdownlint-cli2` | Markdown formatting | MD032 blank lines around lists |
| `Check Tier Label Consistency` | Tier name correctness | Fix tier label ranges |
| `trailing-whitespace` | Strip trailing spaces | Auto-fixed by hook |
| `end-of-file-fixer` | Ensure newline at EOF | Auto-fixed by hook |

### Mojo Format Common Patterns

```mojo
# Long ternary (exceeds 88 chars) → mojo format wraps:
var epsilon = (
    GRADIENT_CHECK_EPSILON_FLOAT32 if dtype
    == DType.float32 else GRADIENT_CHECK_EPSILON_OTHER
)
```

### Mojo Hashable Trait (v0.26.1+) Correct Signature

```mojo
fn __hash__[H: Hasher](self, mut hasher: H):
    hasher.write(value1)
# NOT: fn __hash__(self) -> UInt; NOT: inout hasher; NOT: hasher.update()
```

### Time Savings

- Manual approach: ~2-3 hours (fix each PR individually)
- Batch approach: ~45 minutes
- Savings: ~60-70% time reduction

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Batch merge of 3 documentation PRs | CI fix session 2025-12-29 |
| ProjectOdyssey | 8 PRs created and 4 CI fixes, 2025-12-31 | batch-pr-ci-fixer source |
| ProjectScylla | PRs #1462, #1452 pre-commit fixes, 2026-03-08 | batch-pr-pre-commit-fixes source |
| ProjectMnemosyne | PRs #685-#697 pre-commit fixes, 2026-02-15 | batch-pr-pre-commit-fixes source |
| ProjectOdyssey | 40+ PRs, mojo format root fix + mass rebase, 2026-03-06/07 | mass-pr-ci-fix source |
| ProjectMnemosyne | PR #306 JSON fix + 25 PRs auto-merge, 2026-03-05 | bulk-pr-json-repair-and-automerge source |
| ProjectOdyssey | PR #3189 pre-existing crash fix via rebase, 2026-03-05 | pr-ci-rebase-fix source |
| ProjectScylla | PRs #1739/#1734 ruff-format + test assertion fixes; PR #1737→#1740 src-layout reconstruction, 2026-03-29 | v2.0.0 additions |
