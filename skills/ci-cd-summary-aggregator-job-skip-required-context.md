---
name: ci-cd-summary-aggregator-job-skip-required-context
description: "Fix PRs permanently BLOCKED because a required status-check context is a job gated `if: github.event_name != 'pull_request'`: a whole-job skip does NOT satisfy a required check. Replace per-job required contexts with a single `summary` aggregator job (`if: always()`) that asserts `needs.X.result == 'success'` for must-run jobs and `success|skipped` for jobs designed to skip on PRs; then remove the per-job contexts from branch protection. Use when: (1) branch protection requires a context that the workflow legitimately skips on `pull_request`, (2) PRs are BLOCKED with `skipped` (not failing) required checks, (3) extending a CI workflow with registry/secret-dependent jobs that must skip on forked PRs."
category: ci-cd
date: 2026-05-15
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - github-actions
  - branch-protection
  - required-status-checks
  - aggregator
  - if-always
  - job-skip
  - skipped-conclusion
  - summary-job
---

# CI/CD Summary Aggregator for Job-Skip Required Contexts

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-15 |
| **Objective** | Unblock PRs where a required status-check context is a job that whole-job-skips on `pull_request` events. A `skipped` job conclusion does NOT satisfy a required check in branch protection, so the PR stays BLOCKED indefinitely. |
| **Outcome** | Added a `summary` aggregator job (`if: always()`) that tolerates `skipped` for registry/secret-dependent jobs and asserts `success` for must-run jobs; updated branch protection to require only `summary`. |
| **Verification** | verified-ci — landed in HomericIntelligence/ProjectOdyssey PR #5406, merged commit `da1b3f7e` (2026-05-15). The PR itself was BLOCKED before the branch-protection update and unblocked after. |

## When to Use

- Branch protection requires a context that the workflow legitimately skips on `pull_request` (e.g., image push, SBOM upload, secret-scoped security scan).
- PRs are BLOCKED with required checks reported as `skipped` (not failing) and no path-filter mismatch is at fault.
- You are extending a CI workflow with registry-dependent or secret-dependent jobs that must skip on forked PRs.
- You want one stable required-check name (`summary`) that doesn't grow with the matrix.

## Verified Workflow

> **Verification level:** verified-ci — landed in ProjectOdyssey PR #5406 (merged 2026-05-15). The aggregator + branch-protection update together unblocked the PR.

### Quick Reference

Add a `summary` job to the workflow:

```yaml
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
          echo "build-and-push   = $BUILD_RESULT"
          echo "test-images      = $TEST_IMAGES_RESULT"
          echo "security-scan    = $SECURITY_SCAN_RESULT"
          if [[ "$BUILD_RESULT" != "success" ]]; then
            echo "::error::build-and-push must be 'success' (got: $BUILD_RESULT)"
            fail=1
          fi
          case "$TEST_IMAGES_RESULT" in
            success|skipped) ;;
            *) echo "::error::test-images must be 'success' or 'skipped' (got: $TEST_IMAGES_RESULT)"; fail=1 ;;
          esac
          case "$SECURITY_SCAN_RESULT" in
            success|skipped) ;;
            *) echo "::error::security-scan must be 'success' or 'skipped' (got: $SECURITY_SCAN_RESULT)"; fail=1 ;;
          esac
          exit "$fail"
```

Then update branch protection to require only `summary`:

```bash
ORG=HomericIntelligence; REPO=ProjectOdyssey
gh api repos/$ORG/$REPO/branches/main/protection/required_status_checks --jq '.checks' > /tmp/cur.json
jq '[.[] | select(.context as $c | ["test-images","security-scan","build-and-push (ci)","build-and-push (production)","build-and-push (runtime)"] | index($c) | not)]' /tmp/cur.json > /tmp/new.json
jq -n --slurpfile checks /tmp/new.json '{strict: false, checks: $checks[0]}' > /tmp/patch.json
gh api -X PATCH repos/$ORG/$REPO/branches/main/protection/required_status_checks --input /tmp/patch.json
```

### Detailed Steps

1. **Identify the problem.** Open a BLOCKED PR. In the "Some checks haven't completed yet" / "Required" section, look for contexts marked `Skipped` rather than `Failed`. Confirm those jobs are gated whole-job by `if: github.event_name != 'pull_request'` (or similar conditional excluding the current event).

2. **List the per-job required contexts in branch protection.**

   ```bash
   gh api repos/$ORG/$REPO/branches/main/protection/required_status_checks --jq '.checks[].context'
   ```

3. **Decide must-run vs may-skip for each job.** Jobs that always run on PRs go in the strict (`== 'success'`) set. Jobs that skip on PRs (registry push, SBOM, secret-bearing scans) go in the tolerant (`success|skipped`) set.

4. **Add the aggregator job** (see Quick Reference). Use `if: always()` so it runs even when upstream jobs fail or skip. Use `needs:` to depend on every job whose status must be checked. Assert results explicitly in a `bash` step.

5. **Push the workflow change AND update branch protection in the same logical operation.** The workflow change alone is a no-op for branch protection — until you remove the per-job contexts, those `skipped` results are still blocking.

6. **Verify on a real PR.** Open or push to a PR. Confirm: (a) per-job contexts still post `skipped` but are no longer required, (b) `summary` posts `success` because its assertion gate passed, (c) the PR shows "All checks have passed".

### Why this works (mechanics)

GitHub posts one status-check context per leaf job. A whole-job `if:` evaluating false produces `conclusion=skipped`. Branch protection requires `success` (or, for some neutral conclusions, equivalent) — **`skipped` is not in that satisfying set for job-level skips**. The `summary` aggregator with `if: always()` runs on every event; tolerating `skipped` in its assertion gate makes the aggregator pass on PRs (where registry jobs skip) and push/schedule events (where they run for real). One stable context replaces N brittle ones.

### Alternative (Option A, lower change-cost): demote job-level `if:` to step-level

Remove the job-level `if:` and push the conditional down to the *steps* that need registry access. Add a leading no-op step (`echo "no-op on PR"`) so the job exits `success` on PRs. This satisfies the existing required contexts without a branch-protection edit. PR #5406 chose the aggregator instead because it scales: each new matrix entry adds a `needs:` line, not a new required context to register.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --- | --- | --- | --- |
| Counted on `skipped` to satisfy required check | Assumed a whole-job skip via `if:` would post `success` (because the job "didn't fail") | GitHub posts `conclusion=skipped`; branch protection requires `success` (or specific neutral semantics — `skipped` is not in that set for job-level skips) | Verified empirically: ProjectOdyssey PR #5406 itself was BLOCKED before the branch-protection update landed, even though `test-images`/`security-scan` posted `skipped` cleanly |
| Added the aggregator step but forgot the branch-protection update | Pushed the workflow change first, expecting BLOCKED to clear automatically | Without removing the per-job contexts from required-checks, the new aggregator is a no-op for branch-protection purposes — the per-job contexts are still required and still skipped | Aggregator workflow + branch-protection update are a *single logical fix* — apply both in the same operation (the workflow change is no-op pollution otherwise) |
| Treated this as a path-filter problem | Assumed broadening `paths:` would unblock the PR | Filter fix alone changes the missing-check failure mode from "context never posted" to "context posted as skipped" — both BLOCKED | When required contexts span both flavours, fix both (paths AND aggregator); see companion skill `ci-cd-required-context-never-posts-pr-blocked` |
| Confused with `ci-cd-reusable-workflow-required-checks-aggregator` | Read the existing skill and tried to apply DRY workflow consolidation | That skill is about consolidating duplicate jobs across files; this learning is about the `success`-vs-`skipped` semantics for required contexts | Two aggregator patterns exist: DRY consolidation (reusable `workflow_call`) vs. result-tolerance gate (single workflow). This skill covers the latter |

## Results & Parameters

### Full container-publish summary job (as merged)

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
          echo "build-and-push   = $BUILD_RESULT"
          echo "test-images      = $TEST_IMAGES_RESULT"
          echo "security-scan    = $SECURITY_SCAN_RESULT"
          if [[ "$BUILD_RESULT" != "success" ]]; then
            echo "::error::build-and-push must be 'success' (got: $BUILD_RESULT)"
            fail=1
          fi
          case "$TEST_IMAGES_RESULT" in
            success|skipped) ;;
            *) echo "::error::test-images must be 'success' or 'skipped' (got: $TEST_IMAGES_RESULT)"; fail=1 ;;
          esac
          case "$SECURITY_SCAN_RESULT" in
            success|skipped) ;;
            *) echo "::error::security-scan must be 'success' or 'skipped' (got: $SECURITY_SCAN_RESULT)"; fail=1 ;;
          esac
          exit "$fail"
```

### Full branch-protection PATCH script

```bash
#!/usr/bin/env bash
set -euo pipefail
ORG=HomericIntelligence
REPO=ProjectOdyssey

# 1. Snapshot current required checks
gh api repos/$ORG/$REPO/branches/main/protection/required_status_checks \
  --jq '.checks' > /tmp/cur.json

# 2. Drop the per-job contexts (keep everything else including 'summary')
jq '[
  .[] | select(
    .context as $c |
    [
      "test-images",
      "security-scan",
      "build-and-push (ci)",
      "build-and-push (production)",
      "build-and-push (runtime)"
    ] | index($c) | not
  )
]' /tmp/cur.json > /tmp/new.json

# 3. Build PATCH body
jq -n --slurpfile checks /tmp/new.json \
  '{strict: false, checks: $checks[0]}' > /tmp/patch.json

# 4. Apply
gh api -X PATCH \
  repos/$ORG/$REPO/branches/main/protection/required_status_checks \
  --input /tmp/patch.json

# 5. Verify 'summary' is still required
gh api repos/$ORG/$REPO/branches/main/protection/required_status_checks \
  --jq '.checks[].context' | grep -x summary
```

### Trade-offs

- **Aggregator (chosen for PR #5406):** scales with matrix size; one required context regardless of job count. Cost: workflow edit + branch-protection edit.
- **Step-level `if:` (Option A):** no branch-protection edit needed. Cost: every conditional job must add a no-op success step; less obvious why the job exists at all on PRs.

## Verified On

- **Repo:** HomericIntelligence/ProjectOdyssey
- **PR:** [#5406](https://github.com/HomericIntelligence/ProjectOdyssey/pull/5406)
- **Merged commit:** `da1b3f7e`
- **Date:** 2026-05-15
- **Workflow:** `.github/workflows/container-publish.yml`
- **Branch protection target:** `main` required status checks (`test-images`, `security-scan`, `build-and-push (*)` removed; `summary` retained)
