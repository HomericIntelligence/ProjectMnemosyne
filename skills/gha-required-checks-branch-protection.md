---
name: gha-required-checks-branch-protection
description: "Use when: (1) PRs are permanently BLOCKED because a required status-check context is a job gated by if: github.event_name != 'pull_request' (skipped != satisfied), (2) consolidating duplicate CI jobs into a reusable workflow so _required.yml is a thin aggregator, (3) validating GitHub branch protection API responses and writing synthetic tests for bash enforcement scripts, (4) a summary aggregator job pattern is needed to replace N individual required contexts with one that handles skip semantics correctly, (5) adding a RESULTS-loop aggregator gate to _required.yml with a guard test asserting all non-excluded jobs are wired into needs, (6) guard test needs a provable negative path to catch silently-inverted conditions [verified-local: _unwired_jobs helper pattern, PR #1343], (7) job key vs context name disambiguation for branch protection contexts, (8) GET-before-PUT mitigation for destructive branch protection API, (9) requirements deviation must be disclosed explicitly in implementation plans, (10) you are placing a merge-blocking CI guard and must confirm its job is a pinned required status-check context, not an advisory job — enumerate the ruleset's required contexts and check your target job name is in that set, else the guard is green-but-non-blocking and a regression merges clean, (11) an issue claims a prerequisite PR already 'added'/'landed'/'introduced' a CI job that a new required-context depends on — verify that PR is actually merged to the default branch (gh pr view <n> --json state,mergedAt + grep the file on main) BEFORE adding the context, else the never-posted context bricks the merge queue, (12) you are writing a runbook for a destructive full-replacement API write (branch-protection/ruleset PUT) and must include an explicit ROLLBACK (re-PUT the snapshot on read-back failure), not just a read-back; and derive sibling foreign keys (integration_id) dynamically from the live object rather than hardcoding a literal, (13) verifying a job is a pinned required status-check context in a fleet that uses BOTH org-level and repo-level rulesets — enumerate both and normalize the org `Required Checks / <job>` prefix vs the bare repo form, because checking one ruleset or matching only the bare name yields a false negative/positive on the other, (14) an advisory or scheduled workflow contains a compliance or security check that project documentation claims is 'CI-enforced on every PR' — verify the job is actually wired into the branch-protection required context (e.g. required-checks-gate.needs), not just present in any workflow file; if not, promote it using the 5-step job-promotion pattern (Section M)."
category: ci-cd
date: 2026-06-24
version: "1.9.0"
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
  - guard-test
  - results-loop
  - ci-hardening
  - pinned-context
  - merge-blocking
  - green-but-non-blocking
  - premise-verification
  - prerequisite-pr
  - rollback
  - destructive-put
  - org-ruleset
  - repo-ruleset
  - context-form
  - false-negative
  - dual-ruleset
  - advisory-to-gate-promotion
  - job-promotion-pattern
  - documentation-vs-enforcement-gap
---

# GitHub Actions Required Checks and Branch Protection

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-24 (v1.9.0) · 2026-06-20 (v1.5.0) · 2026-06-14 (v1.4.0) |
| **Objective** | Make required status checks satisfiable and maintainable: handle skip-vs-success semantics with a `summary` aggregator, consolidate duplicate jobs into a reusable `workflow_call` workflow, validate branch-protection API writes with read-back, smoke-test workflow structure, add a RESULTS-loop gate with guard test, and document guard-test negative-path, job-key vs context-name disambiguation, destructive PUT mitigation, requirements-deviation disclosure, (v1.5.0) required-status-check PLACEMENT, and (v1.9.0) promoting a job from an advisory/scheduled workflow to a merge-blocking required check |
| **Outcome** | Consolidated guidance covering eleven interacting concerns; specific cases preserved as examples |
| **Verification** | verified-ci (core patterns); verified-local (section F: _unwired_jobs helper + 3-test pattern, PR #1343; section J: required-context enumeration `jq` query WAS run, returned the listed contexts — but the proposed guard placement itself is **unverified** / planning-only; section K: the prerequisite-PR premise-check technique WAS run — `gh pr view 264` returned OPEN/`mergedAt:null` and the `main` grep returned empty — but the proposed ruleset-edit runbook is **unverified** / planning-only; section L: the reviewer NOGO on issue #284 R0 that motivated the rollback/dynamic-integration_id learning is real and **verified-local**, but the proposed rollback runbook + dynamic-`integration_id` jq merge are **unverified** / planning-only — the ruleset PUT/rollback was NOT executed; section J2 (v1.8.0): the repo-ruleset enumeration leg is **verified-local** (8 bare contexts incl. `schema-validation` returned this session) but the org-ruleset `Required Checks / <job>` prefix parity is **unverified** — documentation-derived from `canonical-checks.md:58-62`, `org-ruleset.json` not opened/grepped this iteration; section M (v1.9.0): all 7 gate tests pass locally + yamllint clean — **verified-local** (issue #1514, ProjectHephaestus)) |

## When to Use

- A PR is permanently **BLOCKED** because a required status-check context is a job gated whole-job by `if: github.event_name != 'pull_request'` (or similar), and the context posts `skipped` rather than `success`.
- You want one stable required-check name (e.g. `summary`) that does not grow as a job matrix grows.
- Two or more workflow files define the same jobs (lint, test, build), so every PR runs them twice and `_required.yml` drifts out of sync.
- You are implementing or tightening GitHub branch protection rules via the API and need to detect silent failures where a PUT is accepted (HTTP 200) but the field is ignored.
- You need to synthetically test a bash branch-protection enforcement script without hitting the live GitHub API.
- An existing workflow-smoke-test gate covers only one workflow and additional critical workflows need regression protection.
- You want a compact `RESULTS` env-var bash-loop aggregator (instead of one env var per job) and a guard unit test that asserts all non-excluded jobs are wired into the gate's `needs:` list — catching gaps automatically as the workflow grows.
- **(v1.5.0)** You are about to ADD a merge-blocking guard (an enforcement-drift assertion, a value-check, a regression guard) and must decide which job/workflow it lives in — a guard placed in a job that is NOT a pinned required status-check context blocks nothing: the PR shows green and a regression merges clean (green-but-non-blocking security-theater). Enumerate the ruleset's required contexts first and confirm your target job `name:` is in that set.
- **(v1.6.0)** An issue's body asserts a prerequisite PR already "added"/"landed"/"introduced" the CI job that POSTS the context you are about to make required (e.g. "PR #264 added the SAST job"). Before writing any runbook ordering that depends on it, VERIFY the PR is actually merged to the default branch (`gh pr view <n> --json state,mergedAt` AND grep the file on `main`). The issue body is a claim, not ground truth — if the posting job is not yet on `main`, adding the required context permanently bricks the merge queue (Section A hazard). Gate the change on the merge.
- **(v1.7.0)** You are writing a runbook for a **destructive full-replacement API write** (a branch-protection or ruleset PUT that overwrites the whole object). A read-back that DETECTS corruption is only half a safeguard — the runbook must also state the explicit ROLLBACK (re-PUT the pre-edit snapshot when the read-back assert fails), and prove BEFORE any PUT that the snapshot itself is a valid restore target (parses + carries the expected pre-edit context count). Separately, when the new array entry must carry a foreign key matching its siblings (e.g. `integration_id`), DERIVE that key from a sibling in the live object via `jq` rather than pasting a literal copied from an issue body or an unmerged diff — the literal is a drift hazard, the derivation is self-consistent by construction.
- **(v1.8.0)** You are verifying that a job is a pinned required status-check context in a fleet that pins checks through BOTH an org-level ruleset AND a repo-level ruleset — and the two use DIFFERENT context-string conventions (the repo ruleset pins the BARE job name `schema-validation` with `integration_id: 15368`; the org ruleset pins the PREFIXED form `Required Checks / schema-validation`). Enumerating only `repo-ruleset.json`, or matching only the bare name (`grep -qx schema-validation`), gives a false negative/positive on the org file. Enumerate BOTH rulesets and normalize the org-vs-repo FORM (`grep -qxE 'schema-validation|Required Checks / schema-validation'`) before asserting membership. This is the inverse detail of Section J: Section J says "place the guard where the context is pinned"; this says "and when you verify that, check both rulesets and both context-string forms, or your verification itself is wrong."
- **(v1.9.0)** An advisory or scheduled workflow contains a compliance or security check that project documentation claims is "CI-enforced on every PR" — verify the job is actually wired into the branch-protection required context (here: `required-checks-gate.needs` in `_required.yml`), not just present in some workflow file. A job that lives only in `security.yml` or any non-gate workflow is advisory regardless of what NOTICE, README, or in-file comments say. When verification reveals the gap, use the 5-step job-promotion pattern (Section M) to promote the job from advisory to merge-blocking. NOTE: the aggregator pattern (this repo's `required-checks-gate` in `_required.yml`) means NO branch-protection PUT is ever needed — just add the job to `_required.yml` and wire it into `required-checks-gate.needs`.

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

```bash
# 5. BEFORE placing a merge-blocking guard: enumerate the REQUIRED status-check
#    contexts from the ruleset, then confirm your target job NAME is in that set.
#    A guard in a non-required job is green-but-non-blocking — a regression merges clean.
jq -r '.rules[] | select(.type=="required_status_checks")
       | .parameters.required_status_checks[].context' configs/github/repo-ruleset.json
# -> lint, unit-tests, integration-tests, security/dependency-scan,
#    security/secrets-scan, build, schema-validation, deps/version-sync

# Prove the placement BLOCKS, not just that the step parses: assert the target job
# name is byte-for-byte one of the pinned contexts (here: schema-validation).
TARGET=schema-validation
jq -r '.rules[]|select(.type=="required_status_checks")
       |.parameters.required_status_checks[].context' configs/github/repo-ruleset.json \
  | grep -qx "$TARGET" \
  || { echo "PLACEMENT BUG: '$TARGET' is NOT a pinned required context — guard blocks nothing"; exit 1; }
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

*Path-filter co-occurrence:* do not mistake this for a `paths:` problem. Broadening the `paths:` filter alone does NOT unblock the PR — it merely flips the failure mode from "context never posted" to "context posted as `skipped`", and **both stay BLOCKED**. When required contexts span both flavours, fix both: correct the `paths:` filter AND add the skip-tolerant aggregator. See the related skill `ci-cd-required-context-never-posts-pr-blocked`.

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

#### E. RESULTS-loop aggregator gate with guard test (planned — unverified)

> **Warning:** This sub-pattern has not been validated end-to-end. It is a planning-phase capture from ProjectHephaestus issue #1315. Treat as a hypothesis until CI confirms.

An alternative to declaring one `env` var per job is a compact `>-` block scalar that builds a space-separated `job=result` string, parsed by a single bash loop. This is more scalable when the gate covers many jobs, because adding a job only requires one `needs:` entry and one line in the block scalar rather than two env-var declarations.

```yaml
# Alternative compact form — one env var covers all jobs
required-checks-gate:
  if: always()
  needs: [lint, unit-tests, integration-tests, type-check, security-scan]
  runs-on: ubuntu-latest
  steps:
    - name: Check all required jobs passed
      env:
        RESULTS: >-
          lint=${{ needs.lint.result }}
          unit-tests=${{ needs.unit-tests.result }}
          integration-tests=${{ needs.integration-tests.result }}
          type-check=${{ needs.type-check.result }}
          security-scan=${{ needs.security-scan.result }}
      run: |
        failed=0
        for pair in $RESULTS; do
          job="${pair%%=*}"
          result="${pair##*=}"
          if [[ "$result" != "success" && "$result" != "skipped" ]]; then
            echo "::error::FAIL: $job -> $result"
            failed=1
          fi
        done
        exit $failed
```

**Key design choices and risks (unverified):**

1. **`>-` block scalar**: strips the trailing newline and collapses all embedded newlines to spaces, producing a single space-separated string. The bash `for pair in $RESULTS` loop then splits on whitespace. This works correctly in standard bash.

2. **Hyphenated job names**: `job="${pair%%=*}"` splits on the first `=`. Since job names may contain hyphens (e.g., `unit-tests`) but not `=`, this is safe. The `##*=` suffix extracts everything after the last `=`. This is the unverified risk: if a job name or result value ever contains `=`, the split breaks.

3. **`skipped` vs `cancelled` semantics**: When a job's `if:` condition evaluates to false on a given event (e.g., `changes-gate` skips on label events), GitHub sets `result: skipped`. The value `cancelled` only appears when the workflow run itself is explicitly cancelled. The bash loop accepts `skipped` as passing, so legitimately-skipped jobs do not block the gate.

4. **Branch protection PUT risk**: Setting `"required_pull_request_reviews": null` in a PUT payload is intended to preserve existing review settings (null = no-op for that field), but this is a destructive API call that has been known to zero out review requirements. Always read-back after PUT. Use `enforce_admins: false` to preserve admin emergency override capability.

**Guard test pattern** — asserts no job is accidentally omitted from the gate's `needs:` list:

```python
import yaml
from pathlib import Path

def test_all_required_jobs_wired_to_gate():
    """Assert required-checks-gate.needs covers every non-excluded job."""
    workflow = yaml.safe_load(
        (Path(".github/workflows/_required.yml")).read_text()
    )
    jobs = workflow["jobs"]
    excluded = {"auto-merge-policy", "pr-policy", "required-checks-gate"}
    all_jobs = set(jobs.keys()) - excluded
    gate_needs = set(jobs["required-checks-gate"]["needs"])
    assert gate_needs == all_jobs, (
        f"Gate missing jobs: {all_jobs - gate_needs}\n"
        f"Gate has extra: {gate_needs - all_jobs}"
    )
```

This guard test catches new jobs added to `_required.yml` that are not wired into the gate, preventing silent bypass of branch protection.

**Exclusion categories:**

| Job Type | Include in Gate? | Reason |
| --------- | ---------------- | ------- |
| Regular CI jobs | YES | Must pass or be skipped |
| Advisory jobs (e.g., `auto-merge-policy`) | NO | Non-blocking by design |
| Jobs with own required context (e.g., `pr-policy`) | NO | Already has own branch-protection entry |
| The gate itself (`required-checks-gate`) | NO | Would create circular `needs:` |

#### F. Guard test with provable negative path (revised pattern — unverified)

> **Verification:** verified-local — implemented in ProjectHephaestus PR #1343 (issue #1338). All 6 tests pass locally; CI validation pending merge. The `_unwired_jobs` helper lives in `hephaestus/ci/required_checks_gate.py`.

The v1.2.0 guard test used a static assertion on the live workflow. A NOGO review identified that this doesn't prove the guard *can* catch a gap — a silently-inverted condition (e.g., `gate_needs - all_jobs` instead of `all_jobs - gate_needs`) would still pass the positive test. Fix: extract a pure helper `_unwired_jobs(wf, excluded)` that can be unit-tested independently with a synthetic workflow dict.

```python
def _unwired_jobs(wf: dict, excluded: frozenset[str]) -> set[str]:
    """Return job keys not wired into the gate's needs: list.

    Args:
        wf: Parsed workflow dict (from yaml.safe_load).
        excluded: Job keys that are not expected to be wired (gate itself,
                  advisory jobs, jobs with their own required context).

    Returns:
        Set of job keys that should be in gate's needs: but are not.
    """
    all_jobs = set(wf.get("jobs", {}).keys())
    gate_needs = set(wf["jobs"]["required-checks-gate"].get("needs", []))
    return (all_jobs - excluded) - gate_needs
```

Three tests required — all three must be present for the guard to be self-verifying:

```python
EXCLUDED = frozenset({"auto-merge-policy", "pr-policy", "required-checks-gate"})

def test_all_required_jobs_wired_positive():
    """Positive: live workflow has no unwired jobs."""
    wf = yaml.safe_load(Path(".github/workflows/_required.yml").read_text())
    assert _unwired_jobs(wf, EXCLUDED) == set(), (
        f"Gate missing jobs: {_unwired_jobs(wf, EXCLUDED)}"
    )

def test_unwired_jobs_detects_gap():
    """Negative: synthetic wf with a dummy-job not in needs → helper returns it."""
    synthetic = {
        "jobs": {
            "required-checks-gate": {"needs": ["lint", "unit-tests"]},
            "lint": {},
            "unit-tests": {},
            "dummy-job": {},   # not in needs
        }
    }
    result = _unwired_jobs(synthetic, EXCLUDED)
    assert result == {"dummy-job"}, f"Expected {{'dummy-job'}}, got {result}"

def test_unwired_jobs_excluded_not_flagged():
    """Excluded jobs (pr-policy, auto-merge-policy) are never flagged."""
    synthetic = {
        "jobs": {
            "required-checks-gate": {"needs": ["lint"]},
            "lint": {},
            "pr-policy": {},
            "auto-merge-policy": {},
        }
    }
    result = _unwired_jobs(synthetic, EXCLUDED)
    assert result == set(), f"Excluded jobs should not be flagged, got {result}"
```

The negative-path test (second) is the critical addition — it proves the helper *can* detect a gap, not just that the current workflow happens to pass.

**Implementation notes (verified-local, PR #1343):**

- **Leaf module, not sub-package:** `hephaestus/ci/required_checks_gate.py` is a leaf module — not a `__init__.py`-based sub-package — to avoid circular imports. See the `dry-refactoring-workflow` skill for the general pattern.
- **`GATE_JOB` constant exported:** the module exports a `GATE_JOB` string constant so tests import it rather than re-defining the string independently.
- **Positive-path test fixture signature:** the positive-path test takes a `workflow` fixture (the full parsed document), NOT a `jobs` fixture, because `_unwired_jobs` calls `wf["jobs"]` internally. Keeping the old `(self, jobs: dict)` signature causes a `KeyError: 'jobs'` (see Failed Attempts).
- **`__init__.py` NOT updated:** `_unwired_jobs` has an underscore prefix (private) and is intentionally not re-exported in `hephaestus/ci/__init__.py`, consistent with the existing convention for internal helpers.

#### G. Job key vs. context name disambiguation

`needs:` in GitHub Actions uses job *keys* — the YAML map key in the `jobs:` block. Branch protection `required_status_checks` contexts use the job `name:` field (the display name). These are usually identical when `name:` is not set explicitly (GitHub defaults the context to the job key). They **diverge** when `name:` contains characters like slashes.

| Scenario | Job key | `name:` field | Context registered |
| -------- | -------- | ------------- | ------------------ |
| No explicit `name:` | `security-dependency-scan` | (absent) | `security-dependency-scan` |
| Slash in `name:` | `security-dependency-scan` | `security/dependency-scan` | `security/dependency-scan` |
| Gate job (always identical) | `required-checks-gate` | `required-checks-gate` | `required-checks-gate` |

**Practical rule:** when setting up branch protection contexts, read the actual context name from a recent CI check-run (`gh api repos/$ORG/$REPO/check-runs --jq '.check_runs[].name'`), not from the job key in the YAML. For the `required-checks-gate` itself, the key and name are always identical because it is defined without a slash.

#### H. Destructive PUT mitigation pattern

`gh api PUT /repos/{owner}/{repo}/branches/main/protection` is a **full-replacement** call — it overwrites ALL protection settings, including fields not mentioned in the payload. A missing field in the payload can silently zero out existing protections (e.g., drop required reviewers).

Required safety pattern:

1. **GET first** — snapshot every current field before touching anything:
   ```bash
   gh api "repos/{owner}/{repo}/branches/main/protection" | tee /tmp/protection-before.json
   ```
2. **Review the snapshot** — especially `required_pull_request_reviews` (reviewer count, dismiss_stale, codeowner reviews) and `required_status_checks.contexts`.
3. **Construct the payload by merging** — copy existing field values into the PUT payload; only change the specific field(s) you intend to modify.
4. **Only PUT after manual field merge** — never construct a PUT payload from scratch without reading the current state first.
5. **Use `enforce_admins: false`** — setting `true` removes admin emergency escape valves (admins can no longer force-push to fix emergencies). Only use `true` if the threat model explicitly requires it.
6. **Note org-level rulesets are NOT affected** — org-level rulesets (e.g., `required_review_thread_resolution`, `required_status_checks` from a ruleset) are configured separately via `gh api repos/{owner}/{repo}/rulesets` and are NOT overwritten by branch-level PUT. Do not confuse the two APIs.

**Preferred alternative for isolated field changes:** use `PATCH` on a sub-resource when available:
```bash
# PATCH only the required_status_checks sub-resource (non-destructive to other fields)
gh api -X PATCH repos/$ORG/$REPO/branches/main/protection/required_status_checks \
  --input /tmp/patch.json
```

#### I. Requirements deviation disclosure pattern

When an implementation plan's approach deviates from the issue's literal text — for example, dropping two `test` contexts from the required list because they are covered by the gate, or changing the set of required reviewers from what the issue specified — the plan MUST explicitly call out the deviation.

**Required disclosure format (in the plan or PR body):**

> **Deviation from issue text:** The issue requested contexts `["lint", "unit-tests", "integration-tests"]` as required checks. This plan instead requires only `["required-checks-gate"]` because the gate's `needs:` already covers all three. This drops `lint` and `unit-tests` as direct required contexts. **Flagged for issue-author confirmation.**

Burying a deviation as an implied consequence of the gate pattern = NOGO. Reviewers will flag it as undisclosed scope change. The pattern applies to any deviation:
- Dropping contexts from the required list (even when logically equivalent via the gate)
- Changing the review count
- Skipping fields the issue mentioned
- Substituting a different API endpoint than the issue specified

The disclosure is cheap (one sentence); the NOGO cycle it prevents is expensive.

#### J. Place a merge-blocking guard in a PINNED required context (planning learning — partly unverified)

> **Verification:** the required-context ENUMERATION technique below is **verified-local** — the
> `jq … required_status_checks[].context` query WAS run during R1 re-planning of ProjectMnemosyne
> issue #309 and returned exactly the eight contexts listed. The proposed guard PLACEMENT (moving
> the assertion into `_required.yml`'s `schema-validation` job) is **UNVERIFIED** — designed at
> planning time only, never implemented and never run in CI. Treat the placement as a proposal,
> the enumeration as a tested technique.

This is the inverse of the hazards in Sections A and G. Sections A/G are about a *deletion/skip*
of a pinned context bricking the merge queue; Section J is about *adding* a guard to a job that was
never pinned in the first place — so it runs, goes green, and **blocks nothing**. A regression
still "merges clean." That is security-theater: green-but-non-blocking.

**The failure that triggered this learning (issue #309, R0 plan):** the new enforcement-drift guard
was placed as a step in `ci.yml`'s `validate` job — the most obvious config-validation job. A
reviewer NOGO'd it (major finding): `validate` is **not** a pinned required status-check context.
Only the jobs whose `name:` appears in the ruleset's `required_status_checks` contexts actually
block a merge. A check living only in `ci.yml` is advisory — green, but never blocking.

**Root-cause resolution (R1 re-planning):**

1. **Enumerate the REQUIRED contexts from the ruleset / branch-protection config** — do not guess
   from workflow filenames:
   ```bash
   jq -r '.rules[] | select(.type=="required_status_checks")
          | .parameters.required_status_checks[].context' configs/github/repo-ruleset.json
   # -> lint, unit-tests, integration-tests, security/dependency-scan,
   #    security/secrets-scan, build, schema-validation, deps/version-sync
   ```
2. **Map each required context to a job `name:`** (NOT a workflow filename — see Section G; GitHub
   pins the job `name:` as the context). Here every required context maps to a job in the canonical
   fleet "required checks" workflow `.github/workflows/_required.yml`. `ci.yml`'s `validate` job is
   **not** in that list, so any check living only in `ci.yml` is advisory.
3. **Place the guard in a job that IS a pinned required context.** The fix moves the assertion into
   `_required.yml`'s `schema-validation` job — a pinned required context that **already loops the
   exact same four ruleset JSON files** (asserting `required_approving_review_count >= 1`). The new
   enforcement-value assertion is a natural sibling step there, reusing the existing file-loop.
4. **Verify BOTH the step exists AND its job is pinned.** Proving the guard "parses" is not enough;
   prove it "blocks." Assert the job `name:` is byte-for-byte one of the ruleset's required contexts
   (`grep -qx <jobname>` against the enumerated set). A guard that runs in a green-but-non-required
   job is worse than no guard — it gives false assurance.

**Generalizable rule:** *before placing any merge-blocking guard, enumerate the repo's
required-status-check contexts from the ruleset/branch-protection config and confirm your target JOB
NAME is in that set.* The job `name:` (not the workflow filename) is the pinned context. Two-sided
verification = step-exists AND job-is-a-pinned-required-context.

**Caveats / unverified reliances for this capture:**

- Only the **repo-level** `configs/github/repo-ruleset.json` was read. The org-level ruleset's
  required contexts were **assumed** to MATCH the repo-level set; if org rules differ, placement
  could still miss. (Enumerate the org ruleset too when in doubt.) **v1.8.0 closes this gap — see
  the sub-finding J2 below: you must enumerate BOTH rulesets AND normalize the org-vs-repo
  context-string FORM before asserting membership.**
- `_required.yml` job `name:` values were assumed byte-for-byte equal to the pinned contexts (the
  workflow's own header comment asserts this), but this was **not** cross-checked against the live
  GitHub branch-protection API — only against the on-disk ruleset JSON.
- `jq` was assumed preinstalled on `ubuntu-latest` (standard, but not asserted by a CI run here).
- **Planning-only:** the guard step + `just` recipe were NOT implemented or CI-run. The
  required-context ENUMERATION was actually executed (verified-local); the proposed placement is
  unverified end-to-end.
- Line numbers (`_required.yml:279-308`, `justfile:694`/`696`) were read at plan time and are
  drift-prone — re-grep at apply time.

**Cross-references (same context-pinning model, inverse hazards):**
`ci-driver-blocked-required-context-drift` and the Section A/G material above document the inverse
hazard — deleting/renaming a pinned context bricks the merge queue; the same model is why
*placement* matters here. See also `ci-hygiene-and-validation-gates` Pattern 4 (pinned-context
constraint), `architecture-executable-convention-guard-pattern` (prose invariant → tested blocking
check), and `config-governance-fix-scope-all-variant-files` (the sibling planning-discipline skill
for issue #309 — verify the issue premise and scope across variant files).

##### J2. A required-context check must span BOTH rulesets AND normalize the org-vs-repo context-string FORM (v1.8.0 — issue #309 R2, partly unverified)

> **Verification:** the REPO-ruleset enumeration leg below is **verified-local** — the
> `jq … required_status_checks[].context` query against `configs/github/repo-ruleset.json` WAS run
> earlier this session and returned the eight bare contexts (incl. `schema-validation`). The
> ORG-ruleset parity leg is **UNVERIFIED** — the `Required Checks / <job>` prefix claim is
> *documentation-derived* from `configs/github/canonical-checks.md:58-62` plus the `_required.yml`
> header comment; `org-ruleset.json` was NOT opened and its `.context` values were NOT grepped this
> iteration. The `ORG REQUIRED` step added below is the check that WOULD confirm it at
> implementation time. `integration_id: 15368` on the repo rulesets is likewise taken from
> canonical-checks.md, not re-confirmed against the live API.

Section J fixed the *placement* of a guard. This is its **inverse detail**: when you *verify* that
placement, the verification itself is wrong if it queries only one ruleset, or matches only one
context-string form. This repo pins required status checks through TWO ruleset forms that use
DIFFERENT context-string conventions (documented in `configs/github/canonical-checks.md:58-62`):

- `repo-ruleset*.json` pin the **BARE** job name, e.g. `schema-validation` (with
  `integration_id: 15368`).
- `org-ruleset*.json` pin the **PREFIXED** form, e.g. `Required Checks / schema-validation`.

**Why "enumerate one ruleset, match the bare name" is a verification bug:**

1. **Enumerating ONLY `repo-ruleset.json` is insufficient.** The org ruleset could pin a different
   (or differently named) set. You must query BOTH `configs/github/repo-ruleset.json` AND
   `configs/github/org-ruleset.json`.
2. **A bare exact match FALSELY reports "not required" against the org file.** A
   `grep -qx schema-validation` against the org ruleset misses, because the org context is literally
   `Required Checks / schema-validation`. Use a form-tolerant matcher:
   `grep -qxE 'schema-validation|Required Checks / schema-validation'`.
3. **Generalizable rule:** when a fleet uses BOTH org-level and repo-level rulesets, a
   placement/verification check for "is this job a required context?" must **(a) enumerate BOTH
   rulesets** and **(b) normalize for the org-vs-repo context-string FORM** (prefixed vs bare)
   before asserting membership. Checking one ruleset, or matching only the bare form, yields a false
   negative/positive on the other.

**Form-tolerant dual-ruleset membership check (replaces the single-file Section J `grep -qx`):**

```bash
for rs in configs/github/repo-ruleset.json configs/github/org-ruleset.json; do
  jq -r '.rules[]|select(.type=="required_status_checks")|.parameters.required_status_checks[].context' "$rs"
done | grep -qxE 'schema-validation|Required Checks / schema-validation' && echo "REQUIRED under both forms"
```

**Caveats for this capture (R2):**

- Repo-level `jq` enumeration WAS run earlier this session (8 bare contexts incl.
  `schema-validation`) → **verified-local**. The org-level leg was NOT run (`org-ruleset.json` not
  opened) → **unverified**; the `Required Checks / <job>` prefix is documentation-derived only.
- `integration_id: 15368` is from `canonical-checks.md`, not re-confirmed against the live API.
- Guard implementation itself remains **planning-only / unverified** (never added or CI-run).
- Line numbers (`canonical-checks.md:58-62`, `_required.yml:279-308`) read at plan time; drift-prone.

#### K. Verify the issue's prerequisite-PR premise before ordering the runbook (planning learning — verified-local technique, unverified runbook)

> **Verification:** the premise-FALSIFICATION technique below is **verified-local** — during
> planning of ProjectMnemosyne issue #284 I actually ran `gh pr view 264 --json state,mergedAt`
> (returned `state: OPEN, mergedAt: null`) and `grep -n "sast" .github/workflows/_required.yml` on
> `main` (returned nothing), observing those results this session. The proposed runbook itself —
> the ruleset PUT that adds `security/sast-scan` to the `homeric-main-baseline` ruleset (id
> 15556487) and its read-back — was **NOT executed**: it is planning-only / **unverified**
> end-to-end. Treat the premise-check as a tested technique, the runbook as a proposal. (Same
> mixed-level shape as Section J.)

This is a planning-discipline lesson that complements Sections A and G. Section A says a required
context whose posting job is skipped/absent bricks the merge queue forever; Section G says the
pinned context is the job `name:`, not the YAML key. Section K is about **where the premise comes
from**: the issue body is a *claim*, not ground truth, and a false past-tense premise INVERTS the
safe ordering of the runbook.

**The failure that triggered this learning (issue #284):** the issue's body asserted *"PR #264
added the `security-sast-scan` CI job to `.github/workflows/_required.yml`"* and asked to add
`security/sast-scan` to the `homeric-main-baseline` ruleset (id 15556487) as a required status
check. Taken at face value, the past-tense "added" reads as already-landed, so the obvious runbook
would add the required context immediately. **Verifying the premise showed it was FALSE on `main`:**

```bash
# 1. Is the prerequisite PR actually merged? (state + mergedAt, not just "exists")
gh pr view 264 --json state,mergedAt
# -> { "state": "OPEN", "mergedAt": null }   # NOT merged

# 2. Is the posting job actually on the default branch?
git checkout main && grep -n "sast" .github/workflows/_required.yml
# -> (no output)   # the job that POSTS security/sast-scan does not exist on main yet
```

**Why this inverts the safety ordering.** Per Section A and the "context never posts → BLOCKED
forever" Failed Attempt: adding a required status-check context whose posting job is NOT yet on
`main` permanently bricks the merge queue — every subsequent PR waits forever for a context that is
never reported. So the ruleset edit MUST be **gated** on PR #264 actually merging first. The issue's
past-tense premise made it sound already done; trusting it would have ordered the ruleset PUT before
the prerequisite existed.

**Generalizable rule:** *when an issue says a prerequisite PR "added"/"landed"/"introduced"
something, verify it is actually merged to the default branch (`gh pr view <n> --json
state,mergedAt` AND grep the file on `main`) BEFORE writing any ordering that depends on it. The
issue body is a claim, not ground truth. Add a HARD prerequisite gate to the runbook — not a
"recommended" step.*

**Sub-learning — context-name verification from an UNMERGED sibling PR's diff.** The pinned context
name is the job `name:` field, not the YAML job key (Section G). Reading PR #264's diff confirmed
job key `security-sast-scan:` posts context `name: security/sast-scan`:

```bash
gh pr diff 264 | grep -iE "sast"
# -> shows  security-sast-scan:   (job key)
#           name: security/sast-scan   (pinned context name)
```

But because PR #264 is **unmerged**, that name is only as stable as the unmerged PR — it could still
change before merge. Re-confirm the context name from the diff at the moment PR #264 merges, not at
plan time, before pinning it into the ruleset.

**Cross-references:** Section A (never-posts → BLOCKED-forever hazard, the consequence this gate
prevents), Section G (job-key vs context-name, the basis for the sub-learning), and
`config-governance-fix-scope-all-variant-files` (the sibling planning-discipline skill that also
turns "verify the issue premise" into explicit pre-work).

#### L. Destructive full-replacement writes need an explicit ROLLBACK, not just a read-back; and derive sibling foreign keys (integration_id) dynamically (planning learning — unverified runbook, verified-local NOGO origin)

> **Verification:** the reviewer NOGO that motivated this section is **verified-local** — during R1
> re-planning of ProjectMnemosyne issue #284 (add `security/sast-scan` to ruleset 15556487 as a
> required status check) the R0 plan actually RECEIVED a NOGO (Grade B) for the concrete gap below,
> and R1 fixed it; that NOGO and its gap are real and were observed this session. The proposed
> rollback runbook and the dynamic-`integration_id` `jq` merge are **UNVERIFIED** / planning-only —
> the ruleset PUT and its rollback were **NOT executed** against the live API or in CI. Treat the
> NOGO origin as real, the runbook as a proposal. (Same mixed-level shape as Sections J and K.)

This extends Section H (GET-before-PUT + read-back for destructive full-replacement writes). Section
H already mandates the snapshot and the read-back. The R0 plan for issue #284 DID take the
`/tmp/ruleset-before.json` snapshot and DID assert a read-back — yet a reviewer still NOGO'd it,
because the plan never stated the **restore action** if the read-back failed. "Snapshot taken,
restore unstated" is the single thing a reviewer wants written down for a runbook whose headline risk
is data loss.

**Learning 1 — a read-back that detects corruption with no restore step is only half a safeguard.**
For any destructive full-replacement API write, the runbook must contain THREE things, not two:
(1) GET snapshot, (2) read-back assert, (3) explicit ROLLBACK = re-PUT the snapshot on assert-failure.
After the read-back, if the asserted invariant fails (e.g. the live required-context count ≠ expected,
or any prior context is missing), **immediately re-PUT the pre-edit snapshot to restore**, then abort
WITHOUT marking the task done (do not close the issue). And BEFORE any PUT, prove the snapshot itself
is a valid restore target — a corrupt snapshot means there is no rollback target at all:

```bash
# 0. PRE-PUT: prove the snapshot is a valid restore target (parses + carries the
#    expected pre-edit context count). A corrupt snapshot = no rollback target.
SNAP=/tmp/ruleset-before.json
gh api "repos/$ORG/$REPO/rulesets/$RULESET_ID" > "$SNAP"
EXPECTED_BEFORE=8   # the pre-edit required-context count you intend to grow to 9
jq empty "$SNAP" || { echo "ABORT: snapshot is not valid JSON — no rollback target"; exit 1; }
before_count=$(jq '[.rules[]|select(.type=="required_status_checks")
                   |.parameters.required_status_checks[]] | length' "$SNAP")
[ "$before_count" = "$EXPECTED_BEFORE" ] \
  || { echo "ABORT: snapshot context count $before_count != expected $EXPECTED_BEFORE — bad restore target"; exit 1; }

# ... (construct merged payload, then PUT) ...
gh api --method PUT "repos/$ORG/$REPO/rulesets/$RULESET_ID" --input /tmp/ruleset-after.json >/dev/null

# 2. READ-BACK ASSERT + 3. ROLLBACK on failure (re-PUT the snapshot, abort, do NOT close issue)
live_count=$(gh api "repos/$ORG/$REPO/rulesets/$RULESET_ID" \
  --jq '[.rules[]|select(.type=="required_status_checks")
        |.parameters.required_status_checks[]] | length')
EXPECTED_AFTER=$((EXPECTED_BEFORE + 1))
if [ "$live_count" != "$EXPECTED_AFTER" ]; then
  echo "::error::read-back assert FAILED (live=$live_count expected=$EXPECTED_AFTER) — ROLLING BACK"
  gh api --method PUT "repos/$ORG/$REPO/rulesets/$RULESET_ID" --input "$SNAP" >/dev/null
  echo "restored pre-edit snapshot; ABORTING without marking task done"
  exit 1
fi
```

**Generalizable rule:** *for any destructive full-replacement API write, the runbook must contain
three steps, not two: (1) GET snapshot, (2) read-back assert, (3) explicit rollback = re-PUT the
snapshot on assert-failure. A read-back that detects corruption but has no restore action is only
half a safeguard. Add a pre-PUT check that the snapshot is a valid restore target (parses + carries
the expected pre-edit context count) before any PUT.*

**Learning 2 — source mutable foreign keys (like `integration_id`) dynamically from a sibling entry
in the same payload, not from a hardcoded literal copied from an issue body.** The R0 plan hardcoded
`integration_id: 15368` straight from the issue body. R1 hardened this: the `jq` merge reads the
`integration_id` off an existing sibling required-status-check entry in the LIVE ruleset and reuses
it for the new entry:

```bash
# Derive integration_id from a sibling required-status-check entry in the live ruleset,
# then append the new context carrying that same id. Self-consistent by construction.
jq '
  (.rules[] | select(.type=="required_status_checks")
            | .parameters.required_status_checks) as $checks
  | ($checks | map(select(.context=="security/dependency-scan")) | .[0].integration_id) as $iid
  | (.rules[] | select(.type=="required_status_checks")
              | .parameters.required_status_checks)
      += [{ "context": "security/sast-scan", "integration_id": $iid }]
' /tmp/ruleset-before.json > /tmp/ruleset-after.json
```

Rationale: a literal copied from an issue body or an unmerged PR diff can silently DRIFT from what
GitHub actually stores (the app/integration may have been reinstalled, the id rotated, or the issue
body simply transcribed wrong). Deriving it from a sibling in the same live object guarantees
consistency with what GitHub actually has. **Generalizable rule:** *when adding an array entry that
must carry a foreign key matching its siblings (app/integration id, owner id, type tag), derive that
key from a sibling in the live object via `jq` (`map(select(.context=="<sibling>")) | .[0].<key>`)
rather than pasting a literal — the literal is a drift hazard, the derivation is self-consistent by
construction.*

**Sub-point — confirm "the context posts at least once" against a SHA where a PR workflow actually
RAN, not against `main` blindly.** A check-run only exists on a commit where the workflow executed.
Query the latest merged PR's head SHA, not `commits/main/check-runs`:

```bash
SHA=$(gh pr list --repo "$ORG/$REPO" --state merged --limit 1 --json headRefOid --jq '.[0].headRefOid')
gh api "repos/$ORG/$REPO/commits/$SHA/check-runs" --jq '.check_runs[].name' | grep -qx "security/sast-scan" \
  || echo "context never posted on a PR-workflow SHA yet — do NOT pin it as required"
```
Querying `commits/main/check-runs` blindly can miss the context simply because the PR workflow never
ran on the `main` HEAD commit, producing a false negative.

**Cross-references:** Section H (GET-before-PUT + read-back — this section adds the missing third leg,
rollback), Section G (job-key vs context-name, the basis for the check-run-SHA sub-point and the
`integration_id` sibling lookup keyed on `context`), Section K (the prerequisite-PR premise check —
same issue #284, the gate that must precede this PUT), and Section A (the never-posts → BLOCKED
hazard the check-run-SHA confirmation guards against).

#### M. Promoting a job from an advisory workflow to a merge-blocking gate (verified-local — issue #1514, ProjectHephaestus)

> **Verification:** **verified-local** — all 7 gate tests pass locally, yamllint clean (2026-06-24,
> ProjectHephaestus issue #1514). The full CI run is pending merge, but the local verification
> suite completed without failures.

**The failure that triggered this learning (issue #1514):** `NOTICE` in ProjectHephaestus claimed
`license-scan` was CI-enforced on every PR. The job existed in `.github/workflows/security.yml`
(an advisory/scheduled workflow), but was NOT wired into `required-checks-gate.needs` in
`.github/workflows/_required.yml`. Because `required-checks-gate` is the SINGLE required context
in branch protection, any job not in its `needs:` list is advisory regardless of documentation.
A PR adding a GPL runtime dependency could merge even if `check_license_compatibility.py` exits 1.

**The documentation-vs-enforcement gap diagnostic:** when project docs, NOTICE files, or PR
descriptions claim a compliance/security check is "CI-enforced on every PR," verify BOTH:
1. The job exists in some workflow file — necessary but NOT sufficient.
2. The job key appears in `required-checks-gate.needs` (or the equivalent aggregator) in
   `_required.yml` — this is what actually blocks a merge.

A job in `security.yml` only (or any non-gate workflow) is advisory, regardless of documentation.

**The 5-step job-promotion pattern (no branch-protection PUT needed):**

> This pattern applies to repos that use the aggregator pattern where a single `required-checks-gate`
> (or `summary`) job fans in all blocking jobs and is itself the only pinned required context.
> No branch-protection PUT is ever needed because the pinned context (`required-checks-gate`)
> is unchanged — only its `needs:` list grows.

**Step 1 — Add the job to `_required.yml`**, placed appropriately in the job dependency order
(e.g., after prerequisite jobs, before the aggregator). Copy the step block from the advisory
workflow exactly, with two adjustments:
- Gate it on `changes-gate.outputs.code_event == 'true'` (like every other heavy job, so it
  skips on label/auto-merge events that don't change code).
- Use `env:` vars for any values from GitHub context that would otherwise require inline
  `${{ }}` interpolation inside shell commands — the safe pattern prevents shell injection:

```yaml
  license-scan:
    needs: [changes-gate, deps-version-sync]
    if: needs.changes-gate.outputs.code_event == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - name: Install package
        run: pip install -e ".[all]"
      - name: Check license compatibility
        env:
          GITHUB_EVENT_NAME: ${{ github.event_name }}
        run: python scripts/check_license_compatibility.py
      - name: Summarize result
        if: always()
        run: echo "License scan complete (event=${{ github.event_name }})" >> "$GITHUB_STEP_SUMMARY"
```

**Step 2 — Add `- <job-key>` to `required-checks-gate.needs`:**

```yaml
  required-checks-gate:
    if: always()
    needs:
      - lint
      - unit-tests
      # ... existing entries ...
      - license-scan   # <-- add this line
    runs-on: ubuntu-latest
    steps:
      - name: Check all required jobs passed
        # ... RESULTS bash-loop unchanged ...
```

**Step 3 — Add `if: github.event_name != 'pull_request'` to the advisory workflow's copy** of
the same job. This matches the existing pattern for `pip-audit`, `sast`, and other jobs that
appear in both `_required.yml` (PR-time gating) and `security.yml` (weekly schedule + manual
dispatch). Without this guard, every PR triggers a duplicate run: one from `_required.yml` and
one from `security.yml`:

```yaml
# In security.yml (advisory / scheduled workflow):
  license-scan:
    if: github.event_name != 'pull_request'   # <-- add this guard
    runs-on: ubuntu-latest
    steps:
      # ... steps unchanged ...
```

**Step 4 — Add a named test asserting the job is in `_required.yml` AND in the gate's `needs:`.**
The guard test (Section F / E) should already cover new jobs automatically via `_unwired_jobs`,
but adding an explicit named assertion creates a permanent acceptance criterion that cannot be
silently removed:

```python
def test_license_scan_is_gated():
    """Explicit acceptance criterion: license-scan must be a gating job (issue #1514)."""
    workflow = yaml.safe_load(Path(".github/workflows/_required.yml").read_text())
    jobs = workflow["jobs"]
    assert "license-scan" in jobs, "license-scan must be a job in _required.yml"
    gate_needs = set(jobs["required-checks-gate"]["needs"])
    assert "license-scan" in gate_needs, "license-scan must be in required-checks-gate.needs"
```

**Step 5 — Validate locally before pushing:**

```bash
yamllint .github/workflows/_required.yml .github/workflows/security.yml
pixi run pytest tests/unit/ci/test_required_checks_gate.py -v
```

**Generalizable rule:** *a compliance or security check in an advisory/scheduled workflow is
advisory regardless of what the documentation says. "The job exists" is necessary but not
sufficient — "the job key is in `required-checks-gate.needs`" is what actually blocks merges.
Promote via the 5-step pattern: (1) add job to `_required.yml` with `changes-gate` guard and
`env:` for context vars, (2) add to gate's `needs:`, (3) add `if: github.event_name !=
'pull_request'` to the advisory copy, (4) add a named test locking the acceptance criterion,
(5) validate locally. No branch-protection PUT needed when the repo uses an aggregator gate.*

**Cross-references:** Section A (job skip → BLOCKED hazard — the inverse of this: adding a job
to the gate when its `if:` skips on PRs); Section E/F (RESULTS-loop aggregator + guard test
patterns that catch promotion gaps automatically); Section J (required-context PLACEMENT — the
same principle from the opposite direction: don't place a guard in a non-required job).

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Counted on `skipped` to satisfy a required check | Assumed a whole-job `if:` skip posts `success` because the job "didn't fail" | GitHub posts `conclusion=skipped`; branch protection requires `success` — `skipped` is not in the satisfying set for job-level skips | Verified empirically (ProjectOdyssey PR #5406 was BLOCKED until the branch-protection update landed); use an `if: always()` aggregator that tolerates `skipped` |
| Pushed the aggregator workflow but forgot the protection edit | Expected BLOCKED to clear once the `summary` job existed | The per-job contexts are still required and still `skipped`; the new aggregator is a no-op for protection | Aggregator workflow + branch-protection edit are a single logical fix — apply both together |
| Treated a BLOCKED PR as purely a path-filter problem | Broadened the `paths:` filter alone, expecting the required context to start passing | Fixing `paths:` only flips the failure mode from "context never posted" to "context posted as `skipped`" — both stay BLOCKED | When required contexts span both flavours, fix both (`paths:` AND the skip-tolerant aggregator); see related skill `ci-cd-required-context-never-posts-pr-blocked` |
| Used `workflow_run` / cross-file `needs:` to aggregate | `workflow_run` to depend on another workflow; `needs:` to reference a job in another file | `workflow_run` fires asynchronously with a different context-name format and does not reliably satisfy required checks; `needs:` only works within one file | Use `workflow_call` (reusable workflows) for required-checks aggregation |
| No read-back after PUT to branch protection | Apply script called `gh api PUT` and exited 0 | API silently ignores unknown/misspelled fields and returns 200; live state unchanged | Always GET read-back immediately after PUT; compare live to expected with jq |
| Exact equality for drift detection | Asserted `required_approving_review_count == 1` | Blocks a valid future tightening to 2 (drift check fails) | Use `>= min_threshold`, not `== exact_value` |
| Wrote smoke tests without reading the workflow | Assumed step names from memory; checked `continue-on-error` across the whole file | Real step name differed; the advisory step legitimately has `continue-on-error: true`, so a global check always fails | Read the workflow first; scope step assertions with a DOTALL step-boundary lookahead |
| Left coverage validator unchanged after matrix→steps migration | Migrated the job to sequential steps without updating `validate_test_coverage.py` | `parse_ci_matrix()` navigated to `strategy.matrix.test-group`, found 0 groups, reported every file uncovered | Add a sequential-steps fallback; collapse `"\\\n"` continuations before regex |
| Used `needs.*.result` wildcard in `if:` expression | Tried `if: needs.*.result != 'failure'` to avoid listing each job explicitly | GitHub Actions does not support `needs.*.result` wildcard expressions in `if:` conditions — the expression is rejected at parse time | List each job individually in env vars or use the RESULTS bash-loop pattern; wildcards are not supported in `needs.*` expressions |
| Guard test without negative path | Static assertion `_unwired_jobs(live_wf, EXCLUDED) == set()` only | Doesn't prove the guard detects gaps — a silently-inverted condition (e.g., `gate_needs - all_jobs` instead of `all_jobs - gate_needs`) still passes the positive test | Extract `_unwired_jobs()` helper; add explicit negative-path test with synthetic wf dict containing a `dummy-job` not in `needs:` |
| `enforce_admins: true` in PUT payload | Set to `true` to "harden" branch protection | Removes admin emergency escape valves; admins can no longer force-push to fix emergencies | Use `false` unless threat model explicitly requires hardened admin lockout |
| Requirements deviation left implicit | Plan dropped two `test` contexts from required list without flagging the deviation | Reviewer flagged as undisclosed scope change (NOGO finding) | Always call out deviations from issue literal text explicitly in the plan or PR body; flag for issue-author confirmation |
| Pass `jobs` dict (not full `wf` dict) to `_unwired_jobs` | Refactored positive-path test kept the `jobs` fixture signature instead of switching to `workflow` | `_unwired_jobs(wf, excluded)` calls `wf["jobs"]` internally; passing the jobs dict directly raises `KeyError: 'jobs'` | Change the positive-path test to accept the `workflow` fixture (full document), not the `jobs` fixture |
| Place the drift guard in ci.yml's `validate` job | Added the enforcement-value assertion as a step in the most obvious config-validation job (`ci.yml`) | `validate` is NOT a pinned required context (only `_required.yml`'s jobs are, per the ruleset's `required_status_checks` contexts); a regression would still merge clean — green-but-non-blocking | Enumerate required contexts from the ruleset (`jq … required_status_checks[].context`) and place the guard in a job whose `name:` is in that set; verify the step's JOB is required, not just that it parses |
| Trusted the issue body's "PR #264 added the SAST job" premise | Planned to add `security/sast-scan` to the ruleset as required, taking the issue's past-tense claim that the posting job already landed at face value | PR #264 was still OPEN (`mergedAt: null`); the job is not on `main`, so the context never posts — adding it as required would permanently block the merge queue (Section A hazard) | Verify prerequisite PRs are actually merged to the default branch (`gh pr view <n> --json state,mergedAt` + grep the file on `main`) before writing runbook ordering that depends on them; gate the change on the merge, don't assume it |
| Destructive ruleset PUT runbook with read-back but no rollback | Planned GET-snapshot + PUT + read-back assert for a full-replacement ruleset write, but left the restore action unstated when the read-back fails | Reviewer NOGO (issue #284 R0, Grade B): a read-back that DETECTS corruption with no restore step is only half a safeguard — the snapshot was taken but never re-PUT | A destructive full-replacement write needs THREE steps: GET snapshot, read-back assert, AND explicit rollback (re-PUT the snapshot on assert-failure); add a pre-PUT check that the snapshot is a valid restore target |
| Hardcoded integration_id literal from the issue body | Copied `integration_id: 15368` from the issue text into the new required-status-check entry | A literal copied from prose/an unmerged diff can drift from what GitHub actually stores | Derive the integration_id from a sibling entry in the live ruleset via jq (`map(select(.context=="<sibling>")) | .[0].integration_id`) — self-consistent by construction |
| Verify required-context membership against repo-ruleset.json with a bare-name exact match | `jq … required_status_checks[].context configs/github/repo-ruleset.json \| grep -qx schema-validation` and stopped there | The ORG ruleset pins the SAME check under a different string form (`Required Checks / schema-validation`) and was not queried at all; a bare `grep -qx` would also have falsely reported "not required" against the org file | Enumerate BOTH org and repo rulesets and match form-tolerantly (`grep -qxE 'name\|Required Checks / name'`); org-vs-repo context strings differ by a `Required Checks / ` prefix (see canonical-checks.md:58-62) |
| Trusted documentation ("CI-enforced on every PR") without verifying gate wiring | `NOTICE` file and in-file comments stated a compliance/security check was CI-enforced on every PR; assumed the job in `security.yml` was merge-blocking | The job existed only in `security.yml` (advisory/scheduled); it was NOT in `required-checks-gate.needs` in `_required.yml` — so it was advisory regardless of documentation; a PR introducing a GPL dependency could merge with exit 1 | "The job exists in a workflow file" is necessary but NOT sufficient; check that the job key appears in `required-checks-gate.needs` (Section M); promote using the 5-step pattern when it does not |

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

### Required-context placement (v1.5.0 — issue #309 R1 re-planning)

**Enumerate the pinned required contexts before placing a merge-blocking guard:**

```bash
# verified-local: this jq query WAS run; returned exactly the eight contexts below.
jq -r '.rules[] | select(.type=="required_status_checks")
       | .parameters.required_status_checks[].context' configs/github/repo-ruleset.json
```

```text
Required status-check contexts (pinned) returned by the query:
  lint
  unit-tests
  integration-tests
  security/dependency-scan
  security/secrets-scan
  build
  schema-validation        <- target job for the new enforcement-value guard
  deps/version-sync

R0 placement (NOGO):  ci.yml job `validate`  -> NOT in the pinned set -> green-but-non-blocking
R1 placement (fixed): _required.yml job `schema-validation` -> pinned -> actually blocks merges
                      (it already loops the same four ruleset JSON files for the
                       required_approving_review_count >= 1 assertion; the new
                       enforcement-value check is a sibling step)
Verification:         enumeration technique = verified-local (jq WAS run);
                      proposed guard placement + just/CI wiring = UNVERIFIED (planning only)
```

**Two-sided placement guard (prove it BLOCKS, not just parses):**

```bash
TARGET=schema-validation   # the job you placed the guard in
jq -r '.rules[]|select(.type=="required_status_checks")
       |.parameters.required_status_checks[].context' configs/github/repo-ruleset.json \
  | grep -qx "$TARGET" \
  || { echo "PLACEMENT BUG: '$TARGET' is NOT a pinned required context"; exit 1; }
```

**Unverified reliances recorded as risks (v1.5.0):**

- Only `configs/github/repo-ruleset.json` was read; org-level ruleset contexts ASSUMED to match.
- `_required.yml` job `name:` values ASSUMED byte-for-byte equal to pinned contexts (per the
  workflow header comment), NOT cross-checked against the live branch-protection API.
- `jq` ASSUMED preinstalled on `ubuntu-latest`; not asserted by a CI run here.
- Guard step + `just` recipe NOT implemented or CI-run (planning only); only the enumeration ran.
- Line numbers (`_required.yml:279-308`, `justfile:694`/`696`) read at plan time; drift-prone.

### Org-vs-repo required-context FORM (v1.8.0 — issue #309 R2)

The fleet pins the SAME required check under two rulesets with DIFFERENT context-string forms
(per `configs/github/canonical-checks.md:58-62`). A membership check must span both files AND
normalize the form, or it produces a false negative/positive:

| Ruleset file | Context-string form | Example | Extra field |
| ------------ | ------------------- | ------- | ----------- |
| `configs/github/repo-ruleset*.json` | BARE job name | `schema-validation` | `integration_id: 15368` |
| `configs/github/org-ruleset*.json` | PREFIXED | `Required Checks / schema-validation` | — |

```bash
# verified-local: repo leg ran (8 bare contexts). org leg UNVERIFIED (org-ruleset.json not opened).
for rs in configs/github/repo-ruleset.json configs/github/org-ruleset.json; do
  jq -r '.rules[]|select(.type=="required_status_checks")|.parameters.required_status_checks[].context' "$rs"
done | grep -qxE 'schema-validation|Required Checks / schema-validation' && echo "REQUIRED under both forms"
```

**Risks:** org-ruleset prefix is documentation-derived (canonical-checks.md), not re-grepped this
iteration; `integration_id: 15368` from canonical-checks.md, not live-API-confirmed; guard itself
planning-only.

## Verified On

| Project | Context | Details |
| ------- | ------- | ------- |
| ProjectOdyssey | PR [#5406](https://github.com/HomericIntelligence/ProjectOdyssey/pull/5406), merged `da1b3f7e` (2026-05-15) | Summary aggregator + branch-protection update; `container-publish.yml`; verified-ci |
| ProjectNestor | Issue #54, PR #108 | Branch-protection API read-back + synthetic tests; verified-ci |
| ProjectOdyssey | PR #4838, issue #3948 | Extended `workflow-smoke-test.yml` to cover 3 more workflows; 26 tests pass |
| ProjectOdyssey | `fix/pixi-env-isolation-signed` branch | Coverage-validator sequential-steps fallback; verified-precommit |
| ProjectMnemosyne | Local branch, yamllint passed | Reusable-workflow `_required.yml`/`_checks.yml` split; verified-precommit |
| ProjectHephaestus | Issue #1315 planning phase | RESULTS-loop aggregator + guard test pattern; **unverified** — not yet implemented or CI-verified |
| ProjectHephaestus | Issue #1315 NOGO review cycle (2026-06-13) | Guard-test negative-path (`_unwired_jobs` helper + 3-test pattern), job-key vs context-name disambiguation, GET-before-PUT mitigation, requirements-deviation disclosure pattern; **unverified** — planning phase captures |
| ProjectHephaestus | Issue #1338 / PR #1343 — extract _unwired_jobs helper | 6/6 tests pass locally; CI pending |
| ProjectMnemosyne | Issue #309 R1 re-planning (2026-06-20) | Section J — required-context PLACEMENT: enumeration `jq` query WAS run (verified-local), returned the 8 pinned contexts; guard placement into `_required.yml`'s `schema-validation` job is **unverified** (planning only) |
| ProjectMnemosyne | Issue #284 planning (2026-06-20) | Section K — prerequisite-PR premise check: `gh pr view 264` returned OPEN/`mergedAt:null` and the `main` grep for `sast` was empty (verified-local); the proposed ruleset PUT adding `security/sast-scan` to ruleset 15556487 is **unverified** (planning only — must be gated on PR #264 merging) |
| ProjectMnemosyne | Issue #284 R1 re-planning (2026-06-20) | Section L — destructive full-replacement write needs explicit ROLLBACK (re-PUT the snapshot on read-back failure), not just a read-back; derive `integration_id` from a live sibling via `jq` instead of hardcoding `15368`. The R0 NOGO (Grade B) that motivated it is real and **verified-local**; the proposed rollback runbook + dynamic-`integration_id` merge are **unverified** (planning only — the ruleset PUT/rollback was NOT executed) |
| ProjectMnemosyne | Issue #309 R2 re-planning (2026-06-20) | Sub-finding J2 — a required-context check must span BOTH org and repo rulesets AND normalize the org `Required Checks / <job>` prefix vs the bare repo form. Repo-ruleset enumeration WAS run (8 bare contexts incl. `schema-validation`) → **verified-local**; the org-ruleset `Required Checks / <job>` prefix parity is **unverified** (documentation-derived from `canonical-checks.md:58-62`; `org-ruleset.json` not opened/grepped this iteration); guard implementation planning-only |
| ProjectHephaestus | Issue #1514 (2026-06-24) | Section M — 5-step job-promotion pattern: `license-scan` promoted from advisory `security.yml`-only to merge-blocking via `_required.yml` + `required-checks-gate.needs`. All 7 gate tests pass locally, yamllint clean. Pattern: (1) add job to `_required.yml` with `changes-gate` guard + `env:` for context vars, (2) add to gate `needs:`, (3) add `if: github.event_name != 'pull_request'` to advisory copy, (4) add named test, (5) validate locally. No branch-protection PUT needed. **verified-local** |

## References

- [GitHub Actions: Reusing workflows](https://docs.github.com/en/actions/using-workflows/reusing-workflows)
- [GitHub Actions: `workflow_call` trigger](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#workflow_call)
- [GitHub: Branch rulesets and required checks](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets)
- [GitHub REST: Update branch protection](https://docs.github.com/en/rest/branches/branch-protection?apiVersion=2022-11-28#update-branch-protection)
