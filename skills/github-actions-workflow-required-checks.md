---
name: github-actions-workflow-required-checks
description: "Canonical guide to GitHub Actions workflow configuration and required status check management. Use when: (1) a PR is blocked because a required status context never posts, (2) reconciling branch protection rulesets with actual job names, (3) diagnosing fan-in / paths-filter / job-skip patterns, (4) adding or removing a required check without breaking open PRs, (5) workflow_dispatch + composite-action wiring, (6) hardening workflows with permissions/concurrency/timeouts, (7) SHA-pinning actions for supply-chain security, (8) runner pool saturation in swarm sessions, (9) pixi caching failures, (10) bot push to protected branch pattern, (11) batch PR CI triage."
category: ci-cd
date: 2026-05-18
version: "1.0.0"
user-invocable: false
verification: verified-local
history: github-actions-workflow-required-checks.history
tags: [merged, github-actions, workflow, required-checks, branch-protection, ruleset]
---

# GitHub Actions Workflow & Required Checks

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-18 |
| **Objective** | Consolidated canonical guide covering GitHub Actions workflow configuration, required status check management, branch protection rulesets, composite actions, fan-in patterns, and CI hardening |
| **Outcome** | Merged from 30 narrow skills (Phase B Wave 1, M2, #1770) |
| **Verification** | verified-local |

## When to Use

- A PR shows `mergeStateStatus: BLOCKED` with no review comments — diagnose via rulesets, not classic branch protection
- Required status context names don't match workflow job names — PRs are permanently blocked
- `on: pull_request` workflows aren't triggering after a push — force-push after rebase to unblock
- Rebasing sibling PRs that each add fan-in entries to `_required.yml` — merge-both-sides rule
- Composite action used before `actions/checkout` — checkout-first invariant violation
- `secrets` context used in job-level `if:` — actionlint error; switch to `vars`
- Pushing an artifact from a workflow to a protected branch — use `peter-evans/create-pull-request`
- Diagnosing multiple failing CI checks across many open PRs — triage by bucket first
- Pixi caching fails with HTTP 400 / "Saved cache with ID -1" — use `actions/cache@v4` explicitly
- Runner pool saturated (`status=queued/`) when dispatching many PRs at once — cap at 5-7 per wave
- SHA-pinning actions for supply-chain security — resolve annotated vs lightweight tags correctly
- Hardening workflows with concurrency, least-privilege permissions, timeouts, gitleaks allowlists

## Verified Workflow

### Quick Reference

```bash
# ── DIAGNOSIS ─────────────────────────────────────────────────────────────────

# 1. Check why a PR is blocked
gh pr view <PR> --json mergeStateStatus,reviewDecision,statusCheckRollup,isDraft
gh pr checks <PR>

# 2. Check classic branch protection (may 404 — also check rulesets)
gh api repos/<OWNER>/<REPO>/branches/main/protection \
  --jq '.required_status_checks.contexts[]'

# 3. Check repository rulesets (works on free plan)
gh api repos/<OWNER>/<REPO>/rulesets
gh api repos/<OWNER>/<REPO>/rulesets/<RULESET_ID>

# 4. Check strict mode setting
gh api repos/<OWNER>/<REPO>/branches/main \
  --jq '.protection.required_status_checks.strict'

# 5. Triage multiple PRs by failing check
gh pr list --state open --limit 100 \
  --json number,title,headRefName,statusCheckRollup \
  --jq '.[] | {number,headRefName,failures:[.statusCheckRollup[]? | select((.conclusion=="FAILURE")) | .name]} | select((.failures|length)>0)'

# ── TRIGGERING CI ─────────────────────────────────────────────────────────────

# Force-push triggers pull_request event (fixes stuck path-filtered CI)
git fetch origin && git rebase origin/main && git push --force-with-lease

# Empty amend when already up-to-date with main
git commit --amend --no-edit && git push --force-with-lease

# ── FAN-IN CONFLICT RESOLUTION ────────────────────────────────────────────────

# _required.yml fan-in: ALWAYS merge-both-sides in:
#   on.workflow_run.workflows: array  (every entry = required check context)
#   fan-in jobs section              (every job = status publisher)
#   concurrency / permissions        (take main)
#   SHA-pinned actions               (take main's newer SHA)

# ── SHA PINNING ───────────────────────────────────────────────────────────────

# Look up an action's commit SHA (handles annotated + lightweight tags)
gha_sha() {
  local owner_repo="$1" tag="$2"
  local result sha type
  result=$(gh api "repos/${owner_repo}/git/ref/tags/${tag}" --jq '.object | {sha, type}')
  sha=$(echo "$result" | jq -r '.sha')
  type=$(echo "$result" | jq -r '.type')
  if [ "$type" = "tag" ]; then
    sha=$(gh api "repos/${owner_repo}/git/tags/${sha}" --jq '.object.sha')
  fi
  echo "  uses: ${owner_repo}@${sha}  # ${tag}"
}
# gha_sha "actions/checkout" "v4"

# Find bare SHA lines missing version comments
grep -rn "uses:.*@[0-9a-f]\{40\}" .github/ | grep -v "#"

# ── HARDENING ─────────────────────────────────────────────────────────────────

# Audit action name alignment between branch protection and workflow files
gh api repos/<OWNER>/<REPO>/branches/main/protection \
  --jq '.required_status_checks.contexts[]' | sort > /tmp/required.txt
grep -rh "name:" .github/workflows/*.yml | sed 's/.*name: //' | sort -u > /tmp/emitted.txt
comm -23 /tmp/required.txt /tmp/emitted.txt  # required but not emitted → blocks PRs

# Check runner saturation
gh run list --workflow="Build and Test" --limit 20 --json status \
  --jq 'group_by(.status) | map({(.[0].status): length}) | add'
# "queued": N → saturation; cap swarm waves at 5-7 concurrent PRs

# ── AUTO-MERGE RECOVERY ───────────────────────────────────────────────────────

# Force-push clears auto-merge silently — always re-arm
git push --force-with-lease origin <branch>
gh pr merge <PR> --auto --rebase
gh pr view <PR> --json autoMergeRequest  # verify not null
```

### Required Check Alignment

GitHub uses `jobs.<id>.name:` as the status check context string. If no `name:` is present, the job ID is used. Branch protection ruleset `required_status_checks.context` must match exactly.

```yaml
# CORRECT — explicit name matches branch protection context
jobs:
  dependency-scan:
    name: security/dependency-scan   # slash in name is valid; slash in job id is not
    runs-on: ubuntu-latest
    steps: [...]
```

**HomericIntelligence `homeric-main-baseline` ruleset** (8 required checks, `integration_id: 15368`):
- `lint`, `unit-tests`, `integration-tests`, `build`, `schema-validation`
- `security/dependency-scan`, `security/secrets-scan`, `deps/version-sync`

Apply ruleset idempotently across all repos (free-plan compatible):
```bash
ORG="HomericIntelligence"
INTEGRATION_ID=15368
for repo in $(gh repo list "$ORG" --json name,isArchived --limit 100 \
    --jq '[.[] | select(.isArchived == false) | .name] | sort | .[]'); do
  existing_id=$(gh api "repos/$ORG/$repo/rulesets" \
    --jq '.[] | select(.name == "homeric-main-baseline") | .id' 2>/dev/null)
  # POST or PUT depending on $existing_id
done
```

### Fan-In Conflict Resolution (`_required.yml`)

When rebasing sibling PRs that each add a new upstream workflow + fan-in job to `_required.yml`:

| Conflict Region | Resolution | Why |
| --------------- | ---------- | --- |
| `on.workflow_run.workflows:` array | Merge both sides — union all entries | Every entry = required check context; drop one → permanent "expected checks not received" |
| Fan-in jobs section | Merge both sides — concatenate job blocks | Each job is a status publisher for a distinct context |
| `concurrency`, `permissions`, top-level `name` | Take `main` | Infrastructure changes; branch copy is stale |
| `uses: actions/<x>@<sha>` | Take `main`'s newer SHA | Newer SHA is at least as audited |
| Dockerfile `apt-get install` | Merge both sides — keep all packages | Apt packages are additive |

### Diagnosing a BLOCKED PR with No Checks

1. `gh pr view <PR> --json mergeStateStatus` → `BLOCKED`, review decision empty
2. `gh pr checks <PR>` → no checks reported
3. `gh api repos/<OWNER>/<REPO>/branches/<DEFAULT>/protection` → may return `404 Branch not protected` (do NOT stop here)
4. `gh api repos/<OWNER>/<REPO>/rulesets` → look for active `code_quality` or `code_scanning` rules
5. `git ls-tree -r --name-only HEAD | grep .github` → if no workflows emit those results, disable those ruleset rules

### `pull_request` Event Not Triggering

**Cause**: path-filtered workflows see zero changed files between empty commit and PR base.

**Fix**: Force push after rebase — GitHub re-evaluates path filters against the new tip SHA:
```bash
git fetch origin && git rebase origin/main && git push --force-with-lease
```

**Do NOT use**: empty `git commit --allow-empty` (no path diff), `gh workflow run` (`workflow_dispatch` does NOT satisfy branch protection required checks), close-and-reopen PR (unreliable).

### `secrets` Context in Job-Level `if:`

`secrets` is unavailable in `if:` at job level — only `env:` and `with:` have access.

```yaml
# WRONG — actionlint error: context "secrets" is not allowed here
jobs:
  deploy:
    if: ${{ secrets.MY_SECRET != '' }}

# CORRECT — use vars (repository variable) for gate; secret via env:
jobs:
  deploy:
    if: ${{ vars.DEPLOY_URL != '' }}    # vars IS allowed in job-level if:
    env:
      DEPLOY_URL: ${{ vars.DEPLOY_URL }}
      API_KEY: ${{ secrets.API_KEY }}
```

### Composite Action: Checkout-First Invariant

Local composite actions (`uses: ./.github/actions/X`) are resolved from disk. `actions/checkout` must precede them in every job.

```python
# Validator helper — skip reusable workflow caller jobs (no steps key)
def _is_reusable_workflow_job(job_data: object) -> bool:
    if not isinstance(job_data, dict):
        return False
    uses = job_data.get("uses", "")
    return isinstance(uses, str) and uses.startswith("./.github/workflows/")
```

Run: `python3 scripts/validate_workflow_checkout_order.py .github/workflows/`

### Bot Push to Protected Branch

**Symptom**: `GH006: Protected branch update failed`

**Fix**: Replace direct push with `peter-evans/create-pull-request` + auto-merge + path-exclusion loop guard:

```yaml
- name: Create PR for generated artifact
  uses: peter-evans/create-pull-request@v7.0.8
  with:
    token: ${{ secrets.GITHUB_TOKEN }}
    commit-message: "chore: regenerate artifact [skip ci]"
    branch: chore/update-artifact
    delete-branch: true

- name: Enable auto-merge
  if: steps.cpr.outputs.pull-request-operation == 'created'
  run: gh pr merge --auto --squash chore/update-artifact
  env:
    GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}

# In on.push.paths, exclude the artifact itself:
# paths:
#   - "skills/**"
#   - "!generated-artifact.json"
```

### Workflow Hardening Checklist

Add to **all** workflows between `on:` and `jobs:`:

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.head_ref || github.sha }}
  cancel-in-progress: true

permissions:
  contents: read   # add packages: write only for registry-push jobs
```

Add `timeout-minutes:` to every job (pre-commit: 30, tests: 30, Docker build: 20-30).

**Gitleaks false positives** — create `.gitleaks.toml`:
```toml
[allowlist]
  description = "Test fixtures and dryrun data"
  paths = ['tests/fixtures/', 'docs/paper-dryrun-data/']
```

**`gitleaks/gitleaks-action@v2` on org repos** requires paid license. Use direct binary download:
```bash
GITLEAKS_VERSION="8.21.2"
curl -sSfL "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz" \
  | tar xz -C /usr/local/bin gitleaks
```

### `strict: false` Branch Protection and Stale CI

`strict_required_status_checks_policy: false` (HomericIntelligence default): passing checks on **any prior commit SHA** satisfy required checks. The latest commit's CI can still be queued when auto-merge fires.

```bash
# Detect strict setting
gh api repos/<ORG>/<REPO>/rulesets \
  --jq '.[] | select(.name == "homeric-main-baseline") | .rules[] | select(.type == "required_status_checks") | .parameters.strict_required_status_checks_policy'

# After force-push, verify readiness via head_sha, not mergeStateStatus (lags)
NEW_SHA=$(git rev-parse HEAD)
gh api "repos/<OWNER>/<REPO>/actions/runs?branch=<branch>" \
  --jq ".workflow_runs[] | select(.head_sha == \"$NEW_SHA\") | {status, conclusion}"
```

### Runner Pool Saturation

GitHub Actions free-tier practical cap: ~80-100 concurrent jobs per org. At ~25 checks/PR, this limits to ~5-7 concurrent PRs before queue depth causes 2+ hour waits.

```bash
# Check saturation before dispatching a wave
gh pr list --state open --json statusCheckRollup \
  --jq '[.[].statusCheckRollup[] | select(.status == "QUEUED" or .status == "IN_PROGRESS")] | length'
# If > 30: wait before dispatching next wave
```

**Cap swarm waves at 5-7 PRs** for heavy matrix repos (multi-OS, multi-compiler, coverage, static analysis).

### Pixi Caching Fix

`prefix-dev/setup-pixi` built-in `cache: true` fails with HTTP 400 / `Saved cache with ID -1` in some environments. Use explicit `actions/cache@v4`:

```yaml
- name: Install pixi
  uses: prefix-dev/setup-pixi@v0.8.1
  with:
    pixi-version: v0.62.2
    # DO NOT use cache: true — broken in some environments

- name: Cache pixi environments
  uses: actions/cache@v4
  with:
    path: |
      .pixi
      ~/.cache/rattler/cache
    key: pixi-${{ runner.os }}-${{ hashFiles('pixi.lock') }}
    restore-keys: |
      pixi-${{ runner.os }}-
```

**Also**: `setup-pixi with cache: true` crashes with "Failed to generate cache key" when `pixi.lock` is absent — always set `cache: false` when the lock file may not exist.

### Batch PR Triage

```bash
# Bucket all open PRs by failing check name
gh pr list --state open --limit 100 \
  --json number,title,headRefName,statusCheckRollup \
  --jq '.[] | {number,title,headRefName,failures:[.statusCheckRollup[]? | select(.conclusion=="FAILURE") | .name]} | select((.failures|length)>0)'

# Identify required vs advisory checks
gh api repos/<OWNER>/<REPO>/branches/main/protection \
  --jq '.required_status_checks.contexts[]'
gh run list --branch main --status failure --limit 5  # pre-existing failures on main = advisory

# Fix root cause on main first when many PRs share the same failure
# Then mass-rebase all affected branches
```

**Classification rules:**

| Pattern | Action |
| ------- | ------ |
| Same check failing on most PRs | Fix root cause on `main` first, then rebase affected branches |
| One PR has extra failing check | Assign targeted fix for that PR only |
| `gh pr checks` shows no checks after force-push | Wait for new workflow run; query head_sha directly |
| Required check failing on `main` itself | Fix `main` first — no PR can satisfy it until base is clean |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| `gh api orgs/<ORG>/rulesets` for org-wide rulesets | Used org-level rulesets endpoint | Returns HTTP 403 on free GitHub plan | Use `repos/<ORG>/<REPO>/rulesets` (repo-level) instead — works on free plan |
| `branches/<default>/protection` to check all policies | Treated HTTP 404 as "no policy" | Repository rulesets can block merges even when classic branch protection returns 404 | When classic branch protection 404s, immediately check `/rulesets` |
| `secrets.SOME_SECRET` in job-level `if:` | Tried `if: ${{ secrets.MY_SECRET != '' }}` | actionlint error: `context "secrets" is not allowed here` — only available in `env:` and `with:` | Use `vars.SOME_VAR` for the job-level gate; pass secret via `env:` |
| Empty commit to re-trigger path-filtered CI | `git commit --allow-empty -m "ci: trigger"` + push | No path diff between empty commit and PR base — path-filtered workflows skip | Force-push after rebase changes the tip SHA and re-evaluates all path filters |
| `workflow_dispatch` to satisfy required checks | `gh workflow run <workflow> --ref <branch>` | Workflow passes but `workflow_dispatch` runs do NOT satisfy branch protection required status checks | CI must be triggered by the `pull_request` event to satisfy required checks |
| Taking one side of `on.workflow_run.workflows:` during rebase | Accepted only the branch's version during conflict | Missing fan-in context → PR permanently BLOCKED with "expected status checks not received" | Always merge-both-sides for the `workflows:` array in `_required.yml` |
| `bats-core/bats-action@2` | Used `@2` major-version alias | The `@2` tag does not exist; only `@1` exists | Always verify action tags against the repo's releases page before using; fall back to `apt-get install bats` |
| SHA lookup via `commits/<tag>` endpoint | Used `repos/<owner>/<repo>/commits/<tag>` | Returns HTTP 422 for annotated tags (point to tag objects, not commits) | Use `git/ref/tags/<tag>` endpoint; if type is "tag" dereference with `git/tags/<sha>` |
| Trusting `mergeStateStatus` after force-push | Checked `gh pr view --json mergeStateStatus` immediately after push | Lags several minutes — shows BLOCKED even when CI is passing | Verify via `gh api .../actions/runs?branch=<branch>` checking `head_sha` matches |
| `setup-pixi cache: true` with absent pixi.lock | Used `cache: true` in a repo without pixi.lock | Crashes with "Failed to generate cache key" before any conditional logic runs | Set `cache: false` when pixi.lock may not exist |
| `gitleaks/gitleaks-action@v2` on org repos | Used official GHA for gitleaks | Requires paid Gitleaks license for org repos — auth errors in CI | Use direct binary download via curl |
| `orgs/<ORG>/rulesets` with `integration_id` absent | Set up required_status_checks without `integration_id` | Checks never satisfied — ruleset can't match against GitHub Actions runs without the app ID | Always include `"integration_id": 15368` (GitHub Actions app ID) in required_status_checks |
| Context string `"Required Checks / lint"` | Used workflow-prefixed form as check context | GitHub reports bare job `name:` values, not workflow-prefixed | Use bare job names: `lint`, `build`, `unit-tests` etc. |
| `setup-pixi@v0.9.5` (nonexistent tag) | Rolled forward to a tag that doesn't exist | Tag not found — immediate job failure | Always verify action tags exist before using; latest was `v0.9.4` |
| `aquasecurity/trivy-action@0.36.0` (no `v` prefix) | Omitted `v` prefix on tag | "Unable to resolve action" | Always include `v` prefix: `@v0.36.0` |
| `markdownlint-cli2-action` with `globs: "**/*.md"` | Explicit glob in action config | Bypasses `.markdownlintignore` — explicit glob overrides the ignore file | Remove `globs:` or add explicit exclusion in the glob |
| Inline `${{ github.base_ref }}` in `run:` | Used template expression directly in shell | Command injection risk; user-controlled input can escape shell | Route `github.base_ref` through `env:` block and reference as `$ENV_VAR` |
| Redundant `actions/cache` in composite action | Added extra cache step on top of `prefix-dev/setup-pixi` with `cache: true` | Duplicate cache keys; inner action already caches `~/.pixi` | Remove extra cache step; let the wrapped action handle its own caching |
| Keeping orphan workflow alongside required checks | Committed `_required.yml` before required-checks list was updated | Workflow ran on every event burning runner minutes without gating any PR | Never commit a workflow whose jobs aren't in the required checks list yet |
| Pushing 14 PRs simultaneously on heavy C++ matrix | Expected parallel CI processing | Runner pool saturated (~350 queued jobs); 0 PRs merged after 2 hours | Cap swarm waves at 5-7 concurrent PRs for heavy matrix repos |

## Results & Parameters

### Key Diagnostic Commands (Copy-Paste Ready)

```bash
# Full PR block diagnosis
gh pr view <PR> --repo <OWNER>/<REPO> \
  --json mergeStateStatus,reviewDecision,statusCheckRollup,isDraft,url
gh api repos/<OWNER>/<REPO>/rulesets
gh api repos/<OWNER>/<REPO>/rulesets/<ID>

# Auto-merge status
gh pr view <PR> --json autoMergeRequest
# Healthy: {"autoMergeRequest": {"mergeMethod": "rebase", ...}}
# Dead:    {"autoMergeRequest": null}

# After force-push: verify via head_sha
NEW_SHA=$(git rev-parse HEAD)
gh api "repos/<OWNER>/<REPO>/actions/runs?branch=<branch>" \
  --jq ".workflow_runs[] | select(.head_sha == \"$NEW_SHA\") | {status, conclusion, name}"
```

### Hardening Audit Template (Before/After)

| Measure | Before | After |
| ------- | ------ | ----- |
| Concurrency block | Missing | `group: workflow-headref/sha; cancel-in-progress: true` |
| `permissions:` | Implicit write | `contents: read` (+ `packages: write` only for push jobs) |
| `timeout-minutes:` | 6h default | 10-30min per job |
| Gitleaks | `gitleaks-action@v2` (paid) | Direct binary `curl` download |
| Pixi cache | `cache: true` (broken) | Explicit `actions/cache@v4` |

### `_required.yml` Minimal Fan-In Template

```yaml
name: Required Checks
on:
  workflow_run:
    workflows:
      - "Build"
      - "Tests"
      # add new upstream workflow names here (never remove)
    types: [completed]

jobs:
  build:
    name: build
    runs-on: ubuntu-latest
    if: github.event.workflow_run.conclusion == 'success'
    steps:
      - run: echo "build passed"

  unit-tests:
    name: unit-tests
    runs-on: ubuntu-latest
    if: github.event.workflow_run.conclusion == 'success'
    steps:
      - run: echo "unit-tests passed"
  # add one job per upstream workflow (job name = required check context)
```

### Verified On

| Project | Context | Details |
| ------- | ------- | ------- |
| HomericIntelligence (all 15 repos) | Ruleset rollout 2026-04-26 | Applied `homeric-main-baseline` via repo-level API |
| HomericIntelligence/ProjectCharybdis | 2026-05-05 — 14 sibling PR rebase wave | Merge-both-sides resolved all `_required.yml` conflicts |
| HomericIntelligence/ProjectAgamemnon | 2026-05-09 PR drainage session | 80+ PRs, 84.7% drain rate; strict=false enabling stale-CI merge |
| HomericIntelligence/ProjectAgamemnon | 2026-05-17 swarm session | Runner saturation at 14 concurrent PRs; capped at 5-7/wave |
| ProjectOdyssey | Various PRs 2026-03–04 | Checkout-order validator, workflow consolidation, pixi caching |
| ProjectHermes | PR #291 | Force-push after rebase triggered path-filtered required checks |
| AchaeanFleet | PR #549 | SHA-pinning with annotated-tag resolution |
| Radiance | PR #33 | Ruleset mismatch diagnosis (code_quality/code_scanning rules) |
| Myrmidons | fix/ci-precommit-parity | `secrets` context in job `if:` — switched to `vars` |

## References

- [GitHub Actions workflow_run trigger](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#workflow_run)
- [GitHub Branch Rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets)
- [Context availability in GitHub Actions](https://docs.github.com/en/actions/learn-github-actions/contexts#context-availability)
- [peter-evans/create-pull-request](https://github.com/peter-evans/create-pull-request)
