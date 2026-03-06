---
name: pr-review-fix-no-op-detection
description: "Detect when a PR review-fix plan requires no code changes and verify the fix commit is pushed. Use when: fix plan says no action needed, CI shows stale failures after a fix commit, or verifying whether a format fix was pushed."
category: ci-cd
date: 2026-03-05
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Skill** | pr-review-fix-no-op-detection |
| **Category** | ci-cd |
| **Trigger** | `.claude-review-fix-*.md` plan file with "no fixes needed" conclusion |
| **Outcome** | Confirm fix commit exists on remote; identify if CI re-run is the only action needed |

## When to Use

- A `.claude-review-fix-<issue>.md` plan file concludes "no fixes are needed" or "already fixed"
- CI shows failures that appear stale (run against an older commit than the fix)
- The fix commit hash is mentioned in the plan but you need to confirm it is on the remote branch
- Pre-commit or mojo-format failures were fixed locally but CI hasn't re-run yet

## Verified Workflow

1. **Read the fix plan** to extract:
   - The fix commit hash (e.g. `1be9b841`)
   - The PR number and branch name
   - Whether failures are claimed to be pre-existing

2. **Check local vs. remote branch divergence:**
   ```bash
   git log --oneline origin/<branch>...<branch> 2>/dev/null
   ```
   - If the fix commit appears here, it exists locally but NOT on remote
   - If empty, local and remote are in sync

3. **Check CI run timestamps vs. fix commit timestamp:**
   ```bash
   gh run list --branch <branch> --limit 5
   ```
   - All runs showing the original commit message = stale; fix not yet triggered CI

4. **Check remote branch HEAD:**
   ```bash
   gh pr view <pr-number> --json headRefOid,headRefName
   ```
   - Compare `headRefOid` to `git log --oneline origin/<branch> -1`

5. **Confirm pre-existing failures on main:**
   ```bash
   gh run list --branch main --workflow "<workflow-name>" --limit 3
   ```
   - If main also shows the same failures, they are pre-existing

6. **Conclusion**: If fix commit is local-only, the only action needed is to push the branch. The plan's "no code changes needed" is correct — only a `git push` is required to trigger CI re-run.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Assumed fix was pushed because plan said "already fixed" | Checked CI status without verifying remote branch | CI showed stale failures from pre-fix run; fix commit was local-only | Always verify `git log origin/<branch>` vs local to confirm push state |
| Declared task complete after reading plan | Did not check `gh run list` timestamps vs. fix commit date | Would have left CI in failing state with unresolved appearance | Cross-check CI run commit message against the fix commit message |
| Checked PR head commit via `gh pr view` | Compared `headRefOid` to local fix commit hash | The PR head was the pre-fix commit; fix was not yet reflected on remote | `headRefOid` from `gh pr view` reflects what GitHub knows, not local state |

## Results & Parameters

### Key Commands (Copy-Paste)

```bash
# 1. Find fix commit hash from plan file
grep -E "commit|fix commit|[0-9a-f]{8}" .claude-review-fix-*.md | head -5

# 2. Check if fix commit is on remote
BRANCH=$(git branch --show-current)
git log --oneline origin/${BRANCH}...${BRANCH}

# 3. Confirm CI runs are against old commit (stale)
gh run list --branch ${BRANCH} --limit 5

# 4. Confirm failures are pre-existing on main
gh run list --branch main --workflow "Pre-commit Checks" --limit 3

# 5. Trigger CI re-run (if authorized to push)
git push origin ${BRANCH}
```

### Diagnosis Matrix

| Local has fix commit | Remote has fix commit | CI shows failures | Action |
|---------------------|----------------------|-------------------|--------|
| Yes | No | Yes (stale) | Push branch to trigger CI re-run |
| Yes | Yes | Yes (stale) | Re-run CI workflow manually via `gh workflow run` |
| Yes | Yes | No | Done - CI is passing |
| No | No | Yes | Fix commit missing; implement the actual fix |

### Stale CI Identification

CI runs are stale when:
- `gh run list --branch <branch>` shows ALL runs with the same (pre-fix) commit message
- The fix commit date is newer than the latest CI run date
- `gh pr view --json headRefOid` shows the pre-fix commit hash
