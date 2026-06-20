---
name: gha-required-checks-branch-protection
description: "Use when: (1) PRs are permanently BLOCKED because a required status-check context is a job gated by if: github.event_name != 'pull_request' (skipped != satisfied), (2) consolidating duplicate CI jobs into a reusable workflow so _required.yml is a thin aggregator, (3) validating GitHub branch protection API responses and writing synthetic tests for bash enforcement scripts, (4) a summary aggregator job pattern is needed to replace N individual required contexts with one that handles skip semantics correctly, (5) adding a RESULTS-loop aggregator gate to _required.yml with a guard test asserting all non-excluded jobs are wired into needs, (6) guard test needs a provable negative path to catch silently-inverted conditions [verified-local: _unwired_jobs helper pattern, PR #1343], (7) job key vs context name disambiguation for branch protection contexts, (8) GET-before-PUT mitigation for destructive branch protection API, (9) requirements deviation must be disclosed explicitly in implementation plans, (10) you are placing a merge-blocking CI guard and must confirm its job is a pinned required status-check context, not an advisory job — enumerate the ruleset's required contexts and check your target job name is in that set, else the guard is green-but-non-blocking and a regression merges clean."
category: ci-cd
date: 2026-06-20
version: "1.5.0"
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
---

# GitHub Actions Required Checks and Branch Protection

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-20 (v1.5.0) · 2026-06-14 (v1.4.0) |
| **Objective** | Make required status checks satisfiable and maintainable: handle skip-vs-success semantics with a `summary` aggregator, consolidate duplicate jobs into a reusable `workflow_call` workflow, validate branch-protection API writes with read-back, smoke-test workflow structure, add a RESULTS-loop gate with guard test, and document guard-test negative-path, job-key vs context-name disambiguation, destructive PUT mitigation, requirements-deviation disclosure, and (v1.5.0) required-status-check PLACEMENT — before placing a merge-blocking guard, enumerate the ruleset's required contexts and confirm the target job is one of them |
| **Outcome** | Consolidated guidance covering ten interacting concerns; specific cases preserved as examples |
| **Verification** | verified-ci (core patterns); verified-local (section F: _unwired_jobs helper + 3-test pattern, PR #1343; section J: required-context enumeration `jq` query WAS run, returned the listed contexts — but the proposed guard placement itself is **unverified** / planning-only) |

## When to Use

- A PR is permanently **BLOCKED** because a required status-check context is a job gated whole-job by `if: github.event_name != 'pull_request'` (or similar), and the context posts `skipped` rather than `success`.
- You want one stable required-check name (e.g. `summary`) that does not grow as a job matrix grows.
- Two or more workflow files define the same jobs (lint, test, build), so every PR runs them twice and `_required.yml` drifts out of sync.
- You are implementing or tightening GitHub branch protection rules via the API and need to detect silent failures where a PUT is accepted (HTTP 200) but the field is ignored.
- You need to synthetically test a bash branch-protection enforcement script without hitting the live GitHub API.
- An existing workflow-smoke-test gate covers only one workflow and additional critical workflows need regression protection.
- You want a compact `RESULTS` env-var bash-loop aggregator (instead of one env var per job) and a guard unit test that asserts all non-excluded jobs are wired into the gate's `needs:` list — catching gaps automatically as the workflow grows.
- **(v1.5.0)** You are about to ADD a merge-blocking guard (an enforcement-drift assertion, a value-check, a regression guard) and must decide which job/workflow it lives in — a guard placed in a job that is NOT a pinned required status-check context blocks nothing: the PR shows green and a regression merges clean (green-but-non-blocking security-theater). Enumerate the ruleset's required contexts first and confirm your target job `name:` is in that set.

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
  could still miss. (Enumerate the org ruleset too when in doubt.)
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

## References

- [GitHub Actions: Reusing workflows](https://docs.github.com/en/actions/using-workflows/reusing-workflows)
- [GitHub Actions: `workflow_call` trigger](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#workflow_call)
- [GitHub: Branch rulesets and required checks](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets)
- [GitHub REST: Update branch protection](https://docs.github.com/en/rest/branches/branch-protection?apiVersion=2022-11-28#update-branch-protection)
