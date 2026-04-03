---
name: github-ruleset-pr-blocked-diagnose-missing-check-requirements
description: "Diagnose GitHub PRs blocked by active rulesets that require checks a repository cannot currently produce. Use when: (1) gh pr view reports mergeStateStatus as BLOCKED with no review comments, (2) gh pr checks reports no checks on the branch, (3) repository rulesets require code quality or code scanning results that the repo is not configured to emit."
category: ci-cd
date: 2026-04-02
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - github
  - rulesets
  - pull-requests
  - codeql
  - branch-governance
---

# GitHub Ruleset PR Blocked: Diagnose Missing Check Requirements

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-02 |
| **Objective** | Identify why a GitHub PR remains blocked after signed commits are fixed and no review feedback exists |
| **Outcome** | Successful — the block was traced to an active repository ruleset requiring `code_quality` and `code_scanning` results in a repo that emitted no checks |
| **Verification** | verified-local |

## When to Use

- `gh pr view <PR> --json mergeStateStatus` returns `BLOCKED` even though review requirements appear satisfied
- `gh pr checks <PR>` says no checks were reported on the branch
- `gh api repos/<OWNER>/<REPO>/branches/<default-branch>/protection` returns `404 Branch not protected`
- The repository is docs-only or otherwise too minimal to produce CodeQL or code-quality results

## Verified Workflow

### Quick Reference

```bash
gh pr view <PR_NUMBER> --repo <OWNER>/<REPO> \
  --json mergeStateStatus,reviewDecision,statusCheckRollup,isDraft,url

gh pr checks <PR_NUMBER> --repo <OWNER>/<REPO>

gh api repos/<OWNER>/<REPO>/branches/<DEFAULT_BRANCH>/protection
gh api repos/<OWNER>/<REPO>/rulesets
gh api repos/<OWNER>/<REPO>/rulesets/<RULESET_ID>

rg --files -g '.github/**'
git ls-tree -r --name-only HEAD
```

### Detailed Steps

1. Confirm the PR is truly blocked and not just awaiting review:
   ```bash
   gh pr view <PR_NUMBER> --repo <OWNER>/<REPO> \
     --json mergeStateStatus,reviewDecision,statusCheckRollup,isDraft,url
   gh pr checks <PR_NUMBER> --repo <OWNER>/<REPO>
   ```
   If merge state is `BLOCKED`, review decision is empty, and `gh pr checks` reports no checks, the blocker is likely policy rather than reviewer action.

2. Check classic branch protection first:
   ```bash
   gh api repos/<OWNER>/<REPO>/branches/<DEFAULT_BRANCH>/protection
   ```
   If GitHub returns `404 Branch not protected`, do **not** stop there. Repository rulesets can still enforce merge requirements even when classic branch protection is absent.

3. Enumerate repository rulesets:
   ```bash
   gh api repos/<OWNER>/<REPO>/rulesets
   gh api repos/<OWNER>/<REPO>/rulesets/<RULESET_ID>
   ```
   Look for active rules like:
   - `required_signatures`
   - `pull_request`
   - `code_quality`
   - `code_scanning`

4. Compare the ruleset with what the repository can actually emit:
   ```bash
   rg --files -g '.github/**'
   git ls-tree -r --name-only HEAD
   ```
   If the repo has no `.github/workflows` or no supported source code for CodeQL/code-quality analysis, required check rules may be impossible to satisfy.

5. Distinguish the signer problem from the ruleset problem:
   ```bash
   gh api repos/<OWNER>/<REPO>/commits/<SHA> --jq '.commit.verification'
   ```
   If commits are already `verified: true` but the PR is still `BLOCKED`, commit signing is no longer the root cause.

6. Form the remediation recommendation:
   - Keep governance rules that the repo can satisfy now, such as signed commits and PR-only merges
   - Remove or disable `code_quality` and `code_scanning` rules until the repository is configured to emit those results
   - Re-enable those rules later, after CodeQL and code-quality workflows are actually present

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Attempt 1 | Queried only `branches/<default>/protection` and treated the `404 Branch not protected` response as proof there was no policy gate | GitHub repository rulesets can block merges independently of classic branch protection | When classic branch protection returns 404, immediately check `/rulesets` before concluding there is no branch policy |
| Attempt 2 | Assumed the PR was still blocked by commit signing after the commits were already verified | The commits were valid, but the merge gate still remained because separate ruleset checks were unsatisfied | Verify commit signatures separately, then continue tracing merge blockers if the PR state stays `BLOCKED` |
| Attempt 3 | Expected `gh pr checks` to reveal the policy source directly | `gh pr checks` only reported that no checks existed, not which ruleset required them | Combine PR state, ruleset API output, and repo inventory to diagnose impossible check requirements |

## Results & Parameters

**Signals that indicate a ruleset mismatch**:

```text
PR mergeStateStatus: BLOCKED
Review decision: empty
PR checks: no checks reported
Branch protection endpoint: 404 Branch not protected
Ruleset includes: code_quality, code_scanning
Repo inventory: no .github/workflows and no meaningful code-scanning surface
```

**Diagnostic commands that worked on a live repo**:

```bash
gh pr view <PR_NUMBER> --repo <OWNER>/<REPO> \
  --json mergeStateStatus,reviewDecision,statusCheckRollup,isDraft,url

gh pr checks <PR_NUMBER> --repo <OWNER>/<REPO>

gh api repos/<OWNER>/<REPO>/branches/<DEFAULT_BRANCH>/protection
gh api repos/<OWNER>/<REPO>/rulesets
gh api repos/<OWNER>/<REPO>/rulesets/<RULESET_ID>

rg --files -g '.github/**'
git ls-tree -r --name-only HEAD
```

**Practical remediation**:

- Keep:
  - signed commits
  - PR-only merges
  - linear history / rebase-only merges
- Temporarily remove or disable:
  - `code_quality`
  - `code_scanning`

until the repo can actually emit those results.

**Why this matters**:

A repository can be governed by a ruleset that is internally consistent in GitHub’s UI but operationally impossible for the repo to satisfy. The symptom is a permanently blocked PR with no checks, no review comments, and no actionable failure surfaced by the standard PR UI.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| Radiance | PR #33 merge-block diagnosis | Verified signed commits were no longer the issue, inspected active rulesets, and traced the remaining block to required `code_quality` and `code_scanning` rules in a repo with no emitted checks |
