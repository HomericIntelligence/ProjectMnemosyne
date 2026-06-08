---
name: gha-required-checks-branch-protection
description: "Use when: (1) PRs are permanently BLOCKED because a required status-check context is a job gated by if: github.event_name != 'pull_request' (skipped != satisfied), (2) consolidating duplicate CI jobs into a reusable workflow so _required.yml is a thin aggregator, (3) validating GitHub branch protection API responses and writing synthetic tests for bash enforcement scripts, (4) a summary aggregator job pattern is needed to replace N individual required contexts with one that handles skip semantics correctly."
category: ci-cd
date: 2026-06-07
version: "1.0.0"
user-invocable: false
history: gha-required-checks-branch-protection.history
tags:
  - github-actions
  - branch-protection
  - required-status-checks
  - reusable-workflow
  - workflow-call
  - aggregator
  - summary-job
  - if-always
  - job-skip
  - api-validation
  - smoke-tests
---

# GitHub Actions Required Checks and Branch Protection

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-07 |
| **Objective** | Make required status checks satisfiable and maintainable: handle skip-vs-success semantics with a `summary` aggregator, consolidate duplicate jobs into a reusable `workflow_call` workflow, validate branch-protection API writes with read-back, and smoke-test workflow structure |
| **Outcome** | Consolidated guidance covering the four interacting concerns; specific cases preserved as examples |
| **Verification** | verified-ci |

## When to Use

- A PR is permanently **BLOCKED** because a required status-check context is a job gated whole-job by `if: github.event_name != 'pull_request'` (or similar), and the context posts `skipped` rather than `success`.
- You want one stable required-check name (e.g. `summary`) that does not grow as a job matrix grows.
- Two or more workflow files define the same jobs (lint, test, build), so every PR runs them twice and `_required.yml` drifts out of sync.
- You are implementing or tightening GitHub branch protection rules via the API and need to detect silent failures where a PUT is accepted (HTTP 200) but the field is ignored.
- You need to synthetically test a bash branch-protection enforcement script without hitting the live GitHub API.
- An existing workflow-smoke-test gate covers only one workflow and additional critical workflows need regression protection.

## Verified Workflow

> **Verification level:** verified-ci — the aggregator + branch-protection pattern landed in HomericIntelligence/ProjectOdyssey PR #5406 (merged `da1b3f7e`, 2026-05-15); the API-validation pattern landed in HomericIntelligence/ProjectNestor PR #108. Some sub-patterns (reusable-workflow split, coverage-step fallback) are verified-precommit only — see Verified On.

### Quick Reference

```yaml
# 1. SUMMARY AGGREGATOR — one required context that tolerates skip on PRs
  summary:
    needs: [build-and-push, test-images, security-scan]
    runs-on: ubuntu-latest
    if: always()
    steps:
      - name: Assert needs results (aggregator gate)
        env:
          BUILD_RESULT: ${{ needs.build-and-push.result }}
          TEST_IMAGES_RESULT: ${{ needs.test-images.result }}
          SECURITY_SCAN_RESULT: ${{ needs.security-scan.result }}
        run: |
          fail=0
          [[ "$BUILD_RESULT" == "success" ]] || { echo "::error::build-and-push must be success (got $BUILD_RESULT)"; fail=1; }
          case "$TEST_IMAGES_RESULT"  in success|skipped) ;; *) echo "::error::test-images bad ($TEST_IMAGES_RESULT)"; fail=1 ;; esac
          case "$SECURITY_SCAN_RESULT" in success|skipped) ;; *) echo "::error::security-scan bad ($SECURITY_SCAN_RESULT)"; fail=1 ;; esac
          exit "$fail"
```

```yaml
# 2. REUSABLE WORKFLOW — _required.yml becomes a thin caller of _checks.yml
# _required.yml
name: Required Checks
on:
  pull_request: { branches: [main] }
  push:         { branches: [main] }
jobs:
  checks:
    uses: ./.github/workflows/_checks.yml
    permissions:
      contents: read   # re-declare; caller permissions do NOT propagate to workflow_call
```

```bash
# 3. BRANCH-PROTECTION API — PUT then read-back to catch silent failures
gh api --method PUT "repos/$ORG/$REPO/branches/main/protection" --input "$CONFIG" >/dev/null
live=$(gh api "repos/$ORG/$REPO/branches/main/protection" \
  --jq '.required_pull_request_reviews.required_approving_review_count // 0')
[ "$live" = "$expected" ] || { echo "ERROR: PUT ignored field; live=$live expected=$expected" >&2; exit 1; }

# 4. Drop per-job required contexts, keep only the aggregator
gh api repos/$ORG/$REPO/branches/main/protection/required_status_checks --jq '.checks' > /tmp/cur.json
jq '[.[] | select(.context as $c | ["test-images","security-scan","build-and-push (ci)"] | index($c) | not)]' \
  /tmp/cur.json > /tmp/new.json
jq -n --slurpfile checks /tmp/new.json '{strict:false, checks:$checks[0]}' > /tmp/patch.json
gh api -X PATCH repos/$ORG/$REPO/branches/main/protection/required_status_checks --input /tmp/patch.json
```

### Detailed Steps

#### A. Summary aggregator for job-skip required contexts

GitHub posts one status-check context per leaf job. A whole-job `if:` evaluating false produces `conclusion=skipped`, and **`skipped` does NOT satisfy a required check** — so a PR that legitimately skips a registry/secret-scoped job stays BLOCKED forever.

1. **Identify the symptom.** On a BLOCKED PR, find required contexts marked `Skipped` (not `Failed`). Confirm those jobs are gated whole-job by `if: github.event_name != 'pull_request'`.
2. **List the current required contexts:**
   ```bash
   gh api repos/$ORG/$REPO/branches/main/protection/required_status_checks --jq '.checks[].context'
   ```
3. **Classify each job** as must-run (assert `== 'success'`) or may-skip (assert `success|skipped`).
4. **Add a `summary` job** with `if: always()` (so it runs even when upstream jobs fail or skip), `needs:` every job whose status matters, and a bash gate asserting results (Quick Reference #1).
5. **Apply the workflow change AND the branch-protection update together.** The workflow edit alone is a no-op for protection — until the per-job contexts are removed, those `skipped` results still block. Remove them and keep only `summary` (Quick Reference #4).
6. **Verify on a real PR:** per-job contexts still post `skipped` but are no longer required; `summary` posts `success`; the PR shows "All checks have passed".

*Lower-cost alternative:* demote the job-level `if:` to step-level and add a leading no-op step so the job exits `success` on PRs. This satisfies the existing contexts with no branch-protection edit, but every conditional job needs a no-op step and the aggregator scales better as the matrix grows (a new matrix entry adds a `needs:` line, not a new registered required context).

#### B. Reusable workflow so `_required.yml` is a thin aggregator

1. **Audit duplication:** identify jobs that appear in both `_required.yml` and another workflow (e.g. `validate-plugins.yml`); confirm they are identical.
2. **Find the exact required-check names.** Cross-reference the ruleset with check-runs on a recent PR:
   ```bash
   gh api repos/$ORG/$REPO/rulesets --jq '.[].conditions'
   gh api repos/$ORG/$REPO/check-runs --jq '.check_runs[].name' | sort -u
   ```
   With `workflow_call`, the context name is the **bare job name** (e.g. `lint`), NOT `Required Checks / lint` — so ruleset entries need no edits.
3. **Create `.github/workflows/_checks.yml`** holding all job definitions under `on: { workflow_call: {} }`.
4. **Rewrite `_required.yml`** to ~20 lines that call it (Quick Reference #2). Re-declare `permissions:` in the caller's job block — caller-level permissions do NOT propagate to `workflow_call` jobs.
5. **Delete the duplicate workflow file** after absorbing any unique steps into `_checks.yml`.
6. **Land both files in one PR.** `uses: ./.github/workflows/_checks.yml` resolves against the PR head branch, so the PR immediately sees its own `_checks.yml`.
7. Validate locally: `yamllint .github/workflows/_checks.yml .github/workflows/_required.yml`.

Use `workflow_call` exclusively — NOT `workflow_run` (asynchronous, different context-name format, does not reliably satisfy required checks) and NOT cross-file `needs:` (only works within one workflow file).

#### C. Branch-protection API validation with read-back + synthetic tests

1. **Scope changes narrowly:** change only fields whose API field-name mapping is verified. Defer unverified fields (e.g. `require_last_push_approval`) to a separate PR.
2. **PUT then GET read-back** on the same endpoint and compare the live value to the expected config via `jq` (Quick Reference #3). This is the only way to catch a 200-but-ignored field. Use defensive jq (`// 0`).
3. **Extract the rules fetch into an overridable function** so a fixture can be injected:
   ```bash
   fetch_rules() {
     if [ -n "${VERIFY_RULES_FIXTURE:-}" ]; then cat "$VERIFY_RULES_FIXTURE"
     else gh api "repos/${REPO}/rules/branches/main"; fi
   }
   ```
4. **Write synthetic pass and fail fixtures** with `jq -n` and run the real script against each, asserting exit 0 / non-zero.
5. **Use `>=` not `==`** for drift detection so a future tightening (1→2 reviews) does not break the check.

#### D. Smoke-test the workflow structure

When a `workflow-smoke-test.yml` gate exists for one workflow and others need protection:

1. **Read each target workflow first** — never assume step names from memory (e.g. a step is `Run mojo format (advisory - non-blocking)`, not `Run mojo format`).
2. **One pytest file per workflow**, grouped by concern (triggers, steps, job deps). Scope step assertions with a DOTALL boundary lookahead so a property check applies to the right step only:
   ```python
   step = re.compile(r"-\s+name:\s+Run mojo format.*?(?=\n\s*-\s+name:|\Z)", re.DOTALL)
   block = step.search(content).group(0)
   assert "continue-on-error: true" in block
   ```
3. **Add a separate CI job** (`smoke-test-other-workflows`) with fast `grep` checks before the heavy `setup-pixi`/`pytest` so regressions fail in seconds, and keep it distinct from the security smoke job for diagnosability.
4. **Add new workflow + test files to the `paths:` filter** of the smoke-test workflow.

*Related parsing pitfall:* if a CI job is migrated from `strategy.matrix.test-group` to sequential named steps, a coverage validator that reads `strategy.matrix` will report 0 covered groups. Add a sequential-steps fallback guarded by `if not groups:` that collapses YAML backslash-newline continuations (`run_cmd.replace("\\\n", " ")`) before regex-extracting `just test-group "<path>" "<pattern>"`, keyed by `f"{step_name}::{path}"`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Counted on `skipped` to satisfy a required check | Assumed a whole-job `if:` skip posts `success` because the job "didn't fail" | GitHub posts `conclusion=skipped`; branch protection requires `success` — `skipped` is not in the satisfying set for job-level skips | Verified empirically (ProjectOdyssey PR #5406 was BLOCKED until the branch-protection update landed); use an `if: always()` aggregator that tolerates `skipped` |
| Pushed the aggregator workflow but forgot the protection edit | Expected BLOCKED to clear once the `summary` job existed | The per-job contexts are still required and still `skipped`; the new aggregator is a no-op for protection | Aggregator workflow + branch-protection edit are a single logical fix — apply both together |
| Used `workflow_run` / cross-file `needs:` to aggregate | `workflow_run` to depend on another workflow; `needs:` to reference a job in another file | `workflow_run` fires asynchronously with a different context-name format and does not reliably satisfy required checks; `needs:` only works within one file | Use `workflow_call` (reusable workflows) for required-checks aggregation |
| No read-back after PUT to branch protection | Apply script called `gh api PUT` and exited 0 | API silently ignores unknown/misspelled fields and returns 200; live state unchanged | Always GET read-back immediately after PUT; compare live to expected with jq |
| Exact equality for drift detection | Asserted `required_approving_review_count == 1` | Blocks a valid future tightening to 2 (drift check fails) | Use `>= min_threshold`, not `== exact_value` |
| Wrote smoke tests without reading the workflow | Assumed step names from memory; checked `continue-on-error` across the whole file | Real step name differed; the advisory step legitimately has `continue-on-error: true`, so a global check always fails | Read the workflow first; scope step assertions with a DOTALL step-boundary lookahead |
| Left coverage validator unchanged after matrix→steps migration | Migrated the job to sequential steps without updating `validate_test_coverage.py` | `parse_ci_matrix()` navigated to `strategy.matrix.test-group`, found 0 groups, reported every file uncovered | Add a sequential-steps fallback; collapse `"\\\n"` continuations before regex |

## Results & Parameters

### Full summary aggregator (as merged, container-publish.yml)

```yaml
  summary:
    needs: [build-and-push, test-images, security-scan]
    runs-on: ubuntu-latest
    if: always()
    steps:
      - name: Write step summary
        run: |
          {
            echo "## Container Publish Summary"
            echo ""
            echo "| Job | Result |"
            echo "| --- | --- |"
            echo "| build-and-push | ${{ needs.build-and-push.result }} |"
            echo "| test-images    | ${{ needs.test-images.result }} |"
            echo "| security-scan  | ${{ needs.security-scan.result }} |"
          } >> "$GITHUB_STEP_SUMMARY"
      - name: Assert needs results (aggregator gate)
        env:
          BUILD_RESULT: ${{ needs.build-and-push.result }}
          TEST_IMAGES_RESULT: ${{ needs.test-images.result }}
          SECURITY_SCAN_RESULT: ${{ needs.security-scan.result }}
        run: |
          fail=0
          [[ "$BUILD_RESULT" == "success" ]] || { echo "::error::build-and-push must be success (got $BUILD_RESULT)"; fail=1; }
          case "$TEST_IMAGES_RESULT"  in success|skipped) ;; *) echo "::error::test-images must be success|skipped (got $TEST_IMAGES_RESULT)"; fail=1 ;; esac
          case "$SECURITY_SCAN_RESULT" in success|skipped) ;; *) echo "::error::security-scan must be success|skipped (got $SECURITY_SCAN_RESULT)"; fail=1 ;; esac
          exit "$fail"
```

### Reusable-workflow final file structure

```text
.github/workflows/
  _checks.yml      # ~279 lines — all job defs, on: workflow_call only
  _required.yml    # ~20 lines  — thin caller, on: pull_request + push
  # validate-plugins.yml deleted; unique steps absorbed into _checks.yml
```

### Branch-protection JSON config + synthetic fixtures

```json
{
  "required_pull_request_reviews": { "required_approving_review_count": 1 },
  "required_status_checks": { "strict": false, "contexts": ["summary", "branch-protection-drift"] },
  "enforce_admins": false,
  "required_conversation_resolution": true,
  "required_linear_history": true
}
```

```bash
# pass fixture -> exit 0
jq -n '[{type:"pull_request",parameters:{required_approving_review_count:1}}]' > "$f"
VERIFY_RULES_FIXTURE="$f" bash scripts/verify-branch-protection.sh   # expect 0
# fail fixture -> exit 1
jq -n '[{type:"pull_request",parameters:{required_approving_review_count:0}}]' > "$f"
VERIFY_RULES_FIXTURE="$f" bash scripts/verify-branch-protection.sh   # expect non-zero
```

### Trade-offs (summary aggregator vs step-level `if:`)

- **Aggregator (chosen for PR #5406):** one required context regardless of job count; scales with the matrix. Cost: workflow edit + branch-protection edit.
- **Step-level `if:`:** no branch-protection edit. Cost: every conditional job needs a no-op success step; less obvious why the job exists on PRs at all.

## Verified On

| Project | Context | Details |
| ------- | ------- | ------- |
| ProjectOdyssey | PR [#5406](https://github.com/HomericIntelligence/ProjectOdyssey/pull/5406), merged `da1b3f7e` (2026-05-15) | Summary aggregator + branch-protection update; `container-publish.yml`; verified-ci |
| ProjectNestor | Issue #54, PR #108 | Branch-protection API read-back + synthetic tests; verified-ci |
| ProjectOdyssey | PR #4838, issue #3948 | Extended `workflow-smoke-test.yml` to cover 3 more workflows; 26 tests pass |
| ProjectOdyssey | `fix/pixi-env-isolation-signed` branch | Coverage-validator sequential-steps fallback; verified-precommit |
| ProjectMnemosyne | Local branch, yamllint passed | Reusable-workflow `_required.yml`/`_checks.yml` split; verified-precommit |

## References

- [GitHub Actions: Reusing workflows](https://docs.github.com/en/actions/using-workflows/reusing-workflows)
- [GitHub Actions: `workflow_call` trigger](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#workflow_call)
- [GitHub: Branch rulesets and required checks](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets)
- [GitHub REST: Update branch protection](https://docs.github.com/en/rest/branches/branch-protection?apiVersion=2022-11-28#update-branch-protection)
