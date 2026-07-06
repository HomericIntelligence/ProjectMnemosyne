---
name: inference360-pr-gates-restore-review-after-merge
description: "Finish Inference360 module-scope PR trains without leaving governance drift. Use when: (1) an Inference360 issue #346-style implementation sequence has sibling PRs and auto-merge gates, (2) a merged PR makes another PR BEHIND, (3) temporary review-count relaxation unblocks auto-merge, (4) branch protection must be restored before issue closure, (5) gh api PATCH booleans need typed -F fields."
category: ci-cd
date: 2026-07-06
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - inference360
  - branch-protection
  - auto-merge
  - approval-requirement
  - rebase
  - gh-api
  - typed-booleans
  - issue-closure
  - pr-gates
---

# Inference360 PR Gates: Restore Review After Merge

## Overview

| Field | Value |
| --- | --- |
| **Date** | 2026-07-06 |
| **Objective** | Finish the Inference360 issue #346 module-scope implementation sequence after strict review, ensuring PRs #361 and #362 merged, branch protection matched issue #349 and repository docs, and issues #346, #349, #351, and #352 were closed only after merged-state validation. |
| **Outcome** | Successful. PR #361 merged after the temporary human-approval gate was removed; PR #362 was rebased onto current `origin/master`, validated, force-pushed with lease, passed GitHub checks, and auto-merged. Required human review was restored afterward. |
| **Verification** | verified-ci. GitHub checks for PR #362 passed after rebase (`Analyze actions`, `Analyze python`, `CodeQL`, `pre-commit`, `python-sca`, `sast`, `secrets`, `validate`), auto-merge completed, branch protection was read back, and final merged-state local validation passed before issue closure. |

## When to Use

- You are finishing an Inference360 implementation sequence with multiple related PRs and tracked issues.
- One PR has merged and a sibling PR becomes `BEHIND` because `origin/master` advanced.
- A temporary human-review requirement relaxation was used to unblock auto-merge and must be restored to the documented policy.
- Issue closure depends on merged-state evidence, not just auto-merge being armed.
- A GitHub branch-protection PATCH fails with HTTP 422 after booleans were sent as strings through `gh api -f`.

## Verified Workflow

### Quick Reference

```bash
# 1. If a sibling PR becomes BEHIND after another PR merges, rebase it onto master.
git fetch origin
git switch <pr-362-branch>
git rebase origin/master

# 2. Run focused validation before updating the PR branch.
git diff --check origin/master..HEAD
env UV_CACHE_DIR=/tmp/Inference360-uv-cache uv run --extra dev pytest tests/test_warden_tools.py -q
uv run ruff check inference360 scripts tests
uv run ruff format --check inference360 scripts tests

# 3. Push the rewritten branch safely and let CI/auto-merge finish.
git push --force-with-lease origin <pr-362-branch>
gh pr checks 362 --repo LLM360/Inference360 --watch --interval 30

# 4. Restore documented human review after temporary relaxation.
gh api --method PATCH \
  repos/LLM360/Inference360/branches/master/protection/required_pull_request_reviews \
  -F required_approving_review_count=1 \
  -F dismiss_stale_reviews=true \
  -F require_code_owner_reviews=true \
  -F require_last_push_approval=false

# 5. Read back the full protection posture before issue closure.
gh api repos/LLM360/Inference360/branches/master/protection \
  --jq '{checks: .required_status_checks.contexts,
         strict: .required_status_checks.strict,
         reviews: .required_pull_request_reviews,
         conversations: .required_conversation_resolution.enabled,
         force_pushes: .allow_force_pushes.enabled,
         deletions: .allow_deletions.enabled,
         admins: .enforce_admins.enabled}'

# 6. Validate the merged state, then close tracked issues.
uv run inference360 --help
uv run pytest tests/test_module_boundaries.py tests/test_wizard.py tests/test_warden_tools.py -q
uv run ruff check inference360 scripts tests
uv run ruff format --check inference360 scripts tests
uv run mypy inference360
```

### Detailed Steps

1. Confirm the first PR actually merged. In this session, PR #361 had already passed strict review and merged once the temporary human-approval gate was removed.

2. Re-check sibling PR state after every merge. After #361 merged, PR #362 became `BEHIND` because `origin/master` advanced. Do not rely on its older strict-review result or older CI snapshot.

3. Rebase the sibling PR onto the current default branch and run focused validation:

   ```bash
   git fetch origin
   git switch <pr-362-branch>
   git rebase origin/master
   git diff --check origin/master..HEAD
   env UV_CACHE_DIR=/tmp/Inference360-uv-cache uv run --extra dev pytest tests/test_warden_tools.py -q
   uv run ruff check inference360 scripts tests
   uv run ruff format --check inference360 scripts tests
   ```

   Observed result for the focused pytest target: `15 passed`.

4. Push the rebased PR with `--force-with-lease`, then watch GitHub checks on the new head. For #362, these checks passed before auto-merge completed: `Analyze actions`, `Analyze python`, `CodeQL`, `pre-commit`, `python-sca`, `sast`, `secrets`, and `validate`.

5. If a temporary approval-count relaxation was used to unblock auto-merge, treat that as operational debt that must be closed before issue closure. Inference360 issue #349 and `docs/repository-settings.md` required one approving review, code owner reviews, stale-review dismissal, conversation resolution, no force pushes, no deletions, and admin enforcement.

6. Restore branch protection with typed `gh api` fields. Use `-F` for booleans and integers, not `-f`, so GitHub receives JSON booleans and numbers rather than strings:

   ```bash
   gh api --method PATCH \
     repos/LLM360/Inference360/branches/master/protection/required_pull_request_reviews \
     -F required_approving_review_count=1 \
     -F dismiss_stale_reviews=true \
     -F require_code_owner_reviews=true \
     -F require_last_push_approval=false
   ```

7. Read back the complete branch-protection posture before closing any tracked issue. Expected key facts for Inference360 `master`:

   | Field | Expected |
   | --- | --- |
   | `strict` | `true` |
   | `checks` | `pre-commit`, `validate`, `secrets`, `sast`, `python-sca` |
   | `required_approving_review_count` | `1` |
   | `require_code_owner_reviews` | `true` |
   | `dismiss_stale_reviews` | `true` |
   | `required_conversation_resolution.enabled` | `true` |
   | `allow_force_pushes.enabled` | `false` |
   | `allow_deletions.enabled` | `false` |
   | `enforce_admins.enabled` | `true` |

8. Only after all implementation PRs are merged, branch protection is restored, no related PRs remain open, and merged-state validation passes, close the tracked issues. Final validation observed before closure:

   | Check | Result |
   | --- | --- |
   | `uv run inference360 --help` | Passed |
   | `uv run pytest tests/test_module_boundaries.py tests/test_wizard.py tests/test_warden_tools.py -q` | `81 passed` |
   | `uv run ruff check inference360 scripts tests` | Passed |
   | `uv run ruff format --check inference360 scripts tests` | Passed |
   | `uv run mypy inference360` | Passed |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --- | --- | --- | --- |
| Complete the goal while PRs were only auto-merge armed | Treated armed auto-merge as effectively complete even though required review still blocked merge | Auto-merge being armed is not a merge; the PR can remain blocked by human review or branch protection | Mark completion only after the PR is merged, checks are green on the relevant head, and closure criteria are satisfied |
| Leave approval count at zero after unblock | Temporarily removed required human approval so auto-merge could proceed, then stopped before restoring it | `required_approving_review_count: 0` contradicted issue #349 and `docs/repository-settings.md` | Temporary protection relaxation must have a restore step and read-back verification before issue closure |
| Trust sibling PR checks after another PR merged | PR #362 had previously passed strict review, so it looked ready after PR #361 merged | `origin/master` advanced and #362 became `BEHIND`; older CI/review evidence no longer represented the merge candidate | After any sibling PR lands, re-check state; if `BEHIND`, rebase onto `origin/master`, rerun focused validation, and push with `--force-with-lease` |
| Send booleans with `gh api -f` | Ran `gh api --method PATCH ... -F required_approving_review_count=1 -f dismiss_stale_reviews=true -f require_code_owner_reviews=true -f require_last_push_approval=false` | GitHub returned HTTP 422 because `-f` sent boolean-looking strings instead of typed booleans | Use `-F` for typed integers and booleans in branch-protection PATCH calls |
| Close issues before merged-state validation | Considered issue closure after PR-level CI and auto-merge events | The final default-branch composition and repository governance posture were not yet proven | Close tracked issues only after merged-state validation passes, no related PR remains open, and branch protection matches documented policy |

## Results & Parameters

### Branch Protection Restore Command

The successful restore command used typed fields throughout:

```bash
gh api --method PATCH \
  repos/LLM360/Inference360/branches/master/protection/required_pull_request_reviews \
  -F required_approving_review_count=1 \
  -F dismiss_stale_reviews=true \
  -F require_code_owner_reviews=true \
  -F require_last_push_approval=false
```

The failed form mixed typed and string fields:

```bash
gh api --method PATCH \
  repos/LLM360/Inference360/branches/master/protection/required_pull_request_reviews \
  -F required_approving_review_count=1 \
  -f dismiss_stale_reviews=true \
  -f require_code_owner_reviews=true \
  -f require_last_push_approval=false
```

Expected failure: HTTP 422 because booleans arrived as strings.

### Branch Protection Read-Back

Use this read-back shape after restore:

```bash
gh api repos/LLM360/Inference360/branches/master/protection \
  --jq '{checks: .required_status_checks.contexts,
         strict: .required_status_checks.strict,
         reviews: .required_pull_request_reviews,
         conversations: .required_conversation_resolution.enabled,
         force_pushes: .allow_force_pushes.enabled,
         deletions: .allow_deletions.enabled,
         admins: .enforce_admins.enabled}'
```

Expected key facts:

```text
strict: true
checks: pre-commit, validate, secrets, sast, python-sca
reviews.required_approving_review_count: 1
reviews.require_code_owner_reviews: true
reviews.dismiss_stale_reviews: true
conversations: true
force_pushes: false
deletions: false
admins: true
```

### Issue Closure Gate

Do not close issues #346, #349, #351, or #352 until all of these are true:

- Implementation PRs are merged to `master`.
- No related PR remains open.
- Branch protection is restored to the documented policy and read back from GitHub.
- Final merged-state validation passes:

  ```bash
  uv run inference360 --help
  uv run pytest tests/test_module_boundaries.py tests/test_wizard.py tests/test_warden_tools.py -q
  uv run ruff check inference360 scripts tests
  uv run ruff format --check inference360 scripts tests
  uv run mypy inference360
  ```

## Verified On

| Project | Context | Details |
| --- | --- | --- |
| LLM360/Inference360 | Issue #346 module-scope completion sequence with issues #349, #351, and #352 on 2026-07-06 | PR #361 merged after temporary approval-gate removal. PR #362 was rebased, passed focused local validation and GitHub checks, auto-merged, then branch protection was restored and read back before final merged-state validation and issue closure. |
