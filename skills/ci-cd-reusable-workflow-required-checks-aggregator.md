---
name: ci-cd-reusable-workflow-required-checks-aggregator
description: "Consolidate duplicate GitHub Actions jobs into a reusable workflow so `_required.yml` is a thin aggregator. Use when: (1) two or more workflow files define the same jobs (lint, test, build), causing every PR to run them twice; (2) you want `_required.yml` to depend on existing CI jobs rather than redefine them; (3) a fat required-checks workflow is drifting out of sync with other workflow files."
category: ci-cd
date: 2026-05-02
version: "1.0.0"
user-invocable: false
verification: verified-precommit
tags: [github-actions, reusable-workflow, workflow-call, required-checks, dry, aggregator]
---

# CI/CD Reusable Workflow Required-Checks Aggregator

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-02 |
| **Objective** | Refactor a monolithic `_required.yml` (~280 lines) that duplicated jobs from `validate-plugins.yml` into a thin aggregator that delegates to a single reusable `_checks.yml` via `workflow_call` |
| **Outcome** | Proposed workflow — yamllint passed locally; CI not yet run |

## When to Use

- Two or more workflow files define the same jobs (e.g., `lint`, `unit-tests`, `build`), causing every PR to run them twice
- `_required.yml` or an equivalent required-checks orchestrator is a 200+ line monolith that duplicates job definitions already maintained elsewhere
- The required-checks workflow is drifting out of sync with other workflow files because changes must be applied in two places
- You need a thin orchestrator for branch ruleset enforcement without rewriting all job logic

## Verified Workflow

> **Verification level:** Pre-commit — `yamllint` passed locally. CI has not yet run at the time of skill creation.

### Quick Reference

```bash
# 1. Create the reusable workflow file
touch .github/workflows/_checks.yml   # all job definitions here

# 2. Rewrite the required-checks orchestrator to ~20 lines
# _required.yml just calls _checks.yml via uses:

# 3. Delete the duplicate workflow file
rm .github/workflows/validate-plugins.yml

# 4. Validate YAML locally
yamllint .github/workflows/_checks.yml .github/workflows/_required.yml

# 5. Verify check context names match ruleset (bare names, no prefix)
gh api repos/<org>/<repo>/check-runs \
  --jq '.check_runs[] | .name' | sort -u
```

### Detailed Steps

1. **Audit the duplication**: Identify which jobs appear in both `_required.yml` and another workflow file. List each job ID and confirm they are truly identical (same steps, same runners).

2. **Check the branch ruleset required check names**: Run `gh api repos/<org>/<repo>/rulesets --jq '.[].conditions'` and cross-reference with `gh api repos/<org>/<repo>/check-runs` on a recent PR to find the exact context names that must pass. These are bare job names (e.g., `lint`, `unit-tests`) — NOT prefixed with the calling workflow name.

3. **Create `.github/workflows/_checks.yml`** as a reusable workflow:

   ```yaml
   name: Checks
   on:
     workflow_call: {}   # no inputs needed for most cases

   jobs:
     lint:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@<sha>
         - run: ruff check .

     unit-tests:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@<sha>
         - run: pytest tests/unit

     # ... all other job definitions
   ```

4. **Rewrite `.github/workflows/_required.yml`** to ~20 lines:

   ```yaml
   name: Required Checks
   on:
     pull_request:
       branches: [main]
     push:
       branches: [main]

   jobs:
     checks:
       uses: ./.github/workflows/_checks.yml
       permissions:
         contents: read
         # re-declare any permissions the callee jobs need
   ```

5. **Delete the now-redundant workflow file** (e.g., `validate-plugins.yml`) — absorb any unique steps (e.g., `ruff check`) into `_checks.yml` first.

6. **Validate locally**:

   ```bash
   yamllint .github/workflows/_checks.yml
   yamllint .github/workflows/_required.yml
   ```

7. **Open a PR** — both `_checks.yml` and the new `_required.yml` land in the same PR. GitHub resolves `uses: ./.github/workflows/_checks.yml` against the PR head branch, so the PR sees its own version of `_checks.yml` immediately.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Attempt 1 | Used `workflow_run` trigger to have `_required.yml` depend on `validate-plugins.yml` completing | Fires asynchronously after the triggering workflow completes; check contexts are prefixed differently and don't satisfy branch ruleset required checks reliably | Use `workflow_call` (reusable workflows), not `workflow_run`, for required-checks aggregation |
| Attempt 2 | Used `needs:` to reference a job from a different workflow file | Not supported — `needs:` only works within the same workflow file | Cross-workflow job dependencies require `workflow_call` to extract jobs into a shared callable workflow |
| Attempt 3 | Deleted `validate-plugins.yml` and kept the fat `_required.yml` unchanged | Makes `_required.yml` the single source but leaves it as a ~280-line monolith, not a thin aggregator; drift problem remains | The reusable workflow split is the only way to achieve both DRY and a thin orchestrator |

## Results & Parameters

### Final File Structure

```
.github/workflows/
  _checks.yml          # ~279 lines — all job definitions, on: workflow_call only
  _required.yml        # ~20 lines  — thin caller, on: pull_request + push
  # validate-plugins.yml deleted — its unique steps absorbed into _checks.yml
```

### Critical Behavior Notes

**Check context name behavior with `workflow_call`**

When a job is defined inside a `workflow_call` callee (`_checks.yml`) and called from a parent workflow (`_required.yml`), GitHub Actions emits check context names as the **bare job name** (e.g., `lint`), NOT prefixed with the calling workflow name (e.g., NOT `Required Checks / lint`). This means branch ruleset entries require **no updates** when adopting this pattern.

**Path resolution for `uses: ./.github/workflows/_checks.yml`**

The relative path `uses: ./.github/workflows/_checks.yml` resolves against the **PR head branch**, not the base branch. Landing both `_checks.yml` and the new `_required.yml` in the same PR is safe — the PR immediately sees its own version of `_checks.yml`.

**Permission propagation**

Top-level `permissions:` on the caller workflow (`_required.yml`) does NOT automatically propagate to `workflow_call` jobs. Re-declare `permissions:` explicitly in the caller's job block:

```yaml
# _required.yml
jobs:
  checks:
    uses: ./.github/workflows/_checks.yml
    permissions:
      contents: read
      checks: write
      # add whatever the callee jobs need
```

**`workflow_run` is NOT a substitute**

`workflow_run` triggers asynchronously (after the triggering workflow finishes) and emits check context names with a different format. It does not reliably satisfy branch ruleset required checks. Use `workflow_call` exclusively for required-checks aggregation.

### Expected Outcome After Merge

- Every PR runs each CI job exactly once (no duplicates)
- `_required.yml` remains ~20 lines — easy to audit and maintain
- All job definitions live in `_checks.yml` — single source of truth
- Ruleset required check names continue to match without any ruleset edits
- `yamllint` passes locally on both workflow files

## Verified On

| Project | Context | Details |
| ------- | ------- | ------- |
| ProjectMnemosyne | Local branch — yamllint passed, awaiting CI | Pre-commit verification only |

## References

- [GitHub Actions: Reusing workflows](https://docs.github.com/en/actions/using-workflows/reusing-workflows)
- [GitHub Actions: `workflow_call` trigger](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#workflow_call)
- [GitHub Actions: `workflow_run` trigger](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#workflow_run)
- [GitHub: Branch rulesets and required checks](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets)
- [skip-reusable-workflow-jobs-in-checkout-validator.md](skip-reusable-workflow-jobs-in-checkout-validator.md)
