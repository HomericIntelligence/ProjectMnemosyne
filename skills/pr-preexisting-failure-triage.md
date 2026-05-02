---
name: pr-preexisting-failure-triage
description: 'Distinguish pre-existing CI failures from regressions introduced by
  a PR, then verify merge readiness. Use when: a PR has CI failures that may not be
  caused by the PR''s own changes.'
category: ci-cd
date: 2026-03-06
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
| ------- | ------- |
| **Goal** | Determine whether CI failures on a PR are pre-existing (safe to ignore) or regressions (must fix) |
| **Input** | PR number, review plan file (`.claude-review-fix-*.md`) |
| **Output** | Triage assessment: which failures are blockers vs pre-existing noise |
| **Trigger** | Review plan says "no fixes needed" but CI shows failures |

## When to Use

- A `.claude-review-fix-*.md` plan states "no fixes required" and "PR is ready to merge"
- CI shows some checks as FAILURE but the PR only touches unrelated files (e.g., workflow YAML vs test code)
- You need to confirm whether failing test groups are affected by the PR's diff before enabling auto-merge
- Determining if `git status` is clean (nothing to commit) matches the plan's assertion that no changes are needed

## Verified Workflow

### Step 1: Read the review plan

Read `.claude-review-fix-<issue>.md` to extract:
- Which deliverables are claimed to be implemented
- Which CI failures are claimed to be pre-existing
- What files were changed

### Step 2: Check git status

```bash
git status
git diff HEAD
```

If the branch is clean (no staged/unstaged changes, no untracked implementation files), the plan's
assertion that "no changes are needed" is confirmed. Only the review plan file itself should be
untracked.

### Step 3: Check PR CI status

```bash
gh pr view <PR_NUMBER> --json state,title,statusCheckRollup
```

For each FAILURE check:
- Note which test group failed (e.g., `Data Datasets`, `Shared Infra`)
- Identify what files the PR touches (`gh pr diff --name-only`)
- Determine if the failing test group's files overlap with PR changes

### Step 4: Classify each failure

| Failure | PR touches those files? | Classification |
| --------- | ------------------------ | ---------------- |
| `Data Datasets` FAIL | No (PR only changed `.github/workflows/`) | Pre-existing |
| `Shared Infra` FAIL | No | Pre-existing |
| `sast-scan` PASS | Yes (workflow files) | Correctly passing |

### Step 5: Confirm no commit needed

If git status is clean and the plan says no changes are needed, there is nothing to commit.
The review plan file (`.claude-review-fix-*.md`) itself should NOT be committed — it is a
working artifact, not an implementation file.

### Step 6: Report outcome

Document findings:
- PR is correctly implemented (all issue deliverables verified)
- Pre-existing failures listed by name with justification
- PR is ready to merge once auto-merge is enabled or approvals received

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Committing review plan file | Treated `.claude-review-fix-*.md` as an implementation artifact to commit | File is a working artifact for the agent, not a deliverable | Only commit actual code/config changes, never the review plan file |
| Looking for additional changes | Searched for uncommitted fixes matching the plan's deliverables | The plan correctly stated all changes were already pushed; branch was clean | When plan says "no fixes required", verify git status first before assuming work remains |
| Retrying tests locally | Attempted to rerun failing CI groups locally to confirm pre-existing status | Unnecessary — PR CI history and test group vs diff analysis is sufficient | Use `gh pr view --json statusCheckRollup` + diff analysis to classify failures without running tests |

## Results & Parameters

### Command to check PR CI status

```bash
gh pr view <PR_NUMBER> --json state,title,statusCheckRollup | \
  python3 -c "import json,sys; checks=json.load(sys.stdin)['statusCheckRollup']; \
  [print(c['conclusion'], c['name']) for c in checks]"
```

### Command to list files changed by PR

```bash
gh pr diff <PR_NUMBER> --name-only
```

### Classification heuristic

If the failing test group's directory (e.g., `tests/shared/infra/`, `tests/data/datasets/`) has
**zero overlap** with the PR's changed files, the failure is pre-existing and not a blocker for
merging.

### Key signals that plan is complete and no commit is needed

1. `git status` shows only the `.claude-review-fix-*.md` as untracked — no modified files
2. `git diff HEAD` is empty
3. Branch is up-to-date with `origin/<branch>`
4. All issue deliverables are verifiable directly in existing committed files
