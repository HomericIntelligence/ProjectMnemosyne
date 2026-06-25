---
name: pr-ci-failure-triage-preexisting-vs-introduced
description: "Use when: (1) a PR has unexpected CI failures and you need to determine if they are PR-introduced or pre-existing main-branch rot before bisecting, reverting, or retriggering, (2) CI fails after a force-push and cancelled runs from the old SHA appear as failures in the PR status rollup, (3) a required CI check fails on a PR whose diff is unrelated to the failing job, (4) CI failures look like flakes (Mojo JIT crash, SIGABRT) and need to be classified before a rerun, (5) stale CI warnings need to be surfaced in PR comments rather than stderr only, (6) CI coverage gate fails because it measures the merge-preview tree rather than the branch alone, (7) a stacked rebased PR has stale CI runs and needs fresh triggering without code changes, (8) sanitizer or compilation jobs fail identically on a PR because stale duplicate commits from another branch are present on the PR branch, (9) deciding whether to fix in-scope, admin-merge, or file a follow-up issue for a blocking failure, (10) a rebased PR has independent CodeQL and validate failures, (11) validate fails only in CI because tests depend on host-specific filesystem auto-detection."
category: ci-cd
date: 2026-06-19
version: "1.1.0"
user-invocable: false
history: pr-ci-failure-triage-preexisting-vs-introduced.history
verification: verified-ci
tags:
  - ci-failure
  - triage
  - preexisting
  - pr-introduced
  - check-runs-api
  - force-push
  - cancelled-runs
  - concurrency-supersession
  - mojo-jit
  - flaky
  - stale-cache
  - admin-merge
  - tracking-issue
  - stale-duplicate-commit
  - post-rebase
  - validate
  - ci-env-drift
  - codeql
---

# PR CI Failure Triage: Pre-Existing vs. PR-Introduced

Classify why CI is red on a pull request — PR-introduced, pre-existing main-branch rot,
flaky, or a status-rollup artifact (cancelled / superseded / stale-cache) — **before**
bisecting, reverting, retriggering, or expanding scope.

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-19 |
| **Objective** | Determine, per failing check, whether a red PR is the PR's fault or a systemic/flaky/artifact failure, then pick the right resolution (fix-in-scope, admin-merge, tracking issue, retrigger, or no-op) |
| **Outcome** | Consolidated from 11 triage skills; authoritative classification via `gh api .../check-runs` on main HEAD; rollup-artifact detection for force-push/concurrency cancellations; flaky-vs-real signatures; stale duplicate-commit detection; post-rebase CodeQL plus validate recovery |
| **Verification** | verified-ci |
| **History** | [changelog](./pr-ci-failure-triage-preexisting-vs-introduced.history) |

## When to Use

- A PR is `BLOCKED` by failing required checks and you must decide fix / admin-merge / issue
- A reviewer labeled failures `PREEXISTING_CI_NOISE` (re-verify — wrong ~2/3 of the time)
- CI is red but the PR diff is unrelated to the failing job (docs-only, config-only, agent-only)
- Failures look like Mojo JIT crashes (`execution crashed`, `SIGABRT`, `libKGENCompilerRTShared.so`)
- A PR shows many red checks right after a rebase / force-push, or right after `gh run rerun`
- `gh pr checks` reports "N fail" but `mergeable=MERGEABLE` and `mergeStateStatus=BLOCKED`
- A required check fails identically across multiple unrelated branches (incl. main)
- All sanitizers fail identically on a PR; the branch carries extra/stale commits
- A stacked PR series is behind main with failures from missing files / stale digests / renamed APIs
- Stale CI pattern warnings exist but only print to stderr, never to the PR comment
- A branch was rebased and now has both security/code-scanning failures and validate-job failures
- Local tests pass but CI validate fails because a test depends on host-specific filesystem
  auto-detection or ambient cluster/container state

## Verified Workflow

### Quick Reference

```bash
# 0. Always unset shadowing tokens first
unset GITHUB_TOKEN GH_TOKEN

# --- AUTHORITATIVE TEST: does each failing check pass on main HEAD? ---
ORG=HomericIntelligence; REPO=ProjectOdyssey; PR=368
gh pr view "$PR" --repo "$ORG/$REPO" --json statusCheckRollup \
  --jq '.statusCheckRollup[] | select(.conclusion == "FAILURE") | .name'
MAIN_SHA=$(gh api "repos/$ORG/$REPO/branches/main" --jq '.commit.sha')
for chk in "<failing-check>"; do
  s=$(gh api "repos/$ORG/$REPO/commits/$MAIN_SHA/check-runs" \
       --jq ".check_runs[] | select(.name==\"$chk\") | .conclusion" | head -1)
  printf "%-30s main=%s\n" "$chk" "${s:-not-run}"
done
# success -> PR-INTRODUCED | failure -> PRE-EXISTING | not-run -> NEW-CHECK

# --- ROLLUP ARTIFACT: real FAILURE vs cancelled/superseded ---
gh pr view "$PR" --json statusCheckRollup --jq '{
  real_failures: [.statusCheckRollup[] | select(.conclusion=="FAILURE") | .name],
  cancelled: ([.statusCheckRollup[] | select(.conclusion=="CANCELLED")] | length)}'

# --- MAIN HISTORY: is the workflow systemically red? ---
gh run list --branch main --workflow "<Workflow>" --limit 10 \
  --json conclusion,createdAt,headSha \
  --jq '.[] | "\(.createdAt)\t\(.conclusion)\t\(.headSha[0:8])"'

# --- gh pr checks valid --json fields (narrow schema!) ---
gh pr checks "$PR" --json name,workflow,state,bucket   # NO status/conclusion/required

# --- Post-rebase recovery / final state confirmation ---
git -c core.editor=true rebase --continue
gh pr checks "<pr>" --repo "<owner>/<repo>"
gh pr view "<pr>" --repo "<owner>/<repo>" \
  --json mergeStateStatus,mergeable,headRefOid,url

# --- Retrigger ONLY failed jobs (after classifying as flake) ---
gh run rerun <run-id> --failed
```

### Detailed Steps

#### 1. Authoritative classification via the check-runs API (do this first)

The fastest, most authoritative test is whether each failing **check name** (not workflow
name) passes on main HEAD. A ~5-second `check-runs` query overrides any reviewer label.

- Use the EXACT `name` from `statusCheckRollup` — that is the required-status-check context
  branch protection enforces. A workflow can show FAILURE while its required sub-job PASSED.
- `success` on main → **PR-INTRODUCED** (fix in this PR). `failure` → **PRE-EXISTING**
  (use the resolution ladder; do NOT expand scope). `not-run` → **NEW-CHECK** (added by the
  branch; investigate).
- ALWAYS re-verify reviewer `PREEXISTING_CI_NOISE` labels — empirically wrong 2 of 3 times
  (Agamemnon #368 markdownlint+trivy and Hermes #614 urllib3 CVE were actually PR-introduced).
- File-overlap (failing test not in the diff) is a hint, not proof — a check can fail from
  env/config drift unrelated to file paths. The check-runs API is the only authoritative test.

Full diagnostic script:

```bash
#!/usr/bin/env bash
set -euo pipefail
unset GITHUB_TOKEN GH_TOKEN
ORG="${1:?}" REPO="${2:?}" PR="${3:?}"
mapfile -t FAILING < <(gh pr view "$PR" --repo "$ORG/$REPO" --json statusCheckRollup \
  --jq '.statusCheckRollup[] | select(.conclusion == "FAILURE") | .name')
[ "${#FAILING[@]}" -eq 0 ] && { echo "No failing required checks."; exit 0; }
MAIN_SHA=$(gh api "repos/$ORG/$REPO/branches/main" --jq '.commit.sha')
for chk in "${FAILING[@]}"; do
  s=$(gh api "repos/$ORG/$REPO/commits/$MAIN_SHA/check-runs" \
       --jq ".check_runs[] | select(.name == \"$chk\") | .conclusion" | head -1)
  case "${s:-not-run}" in
    success) v="PR-INTRODUCED (fix here)";;
    failure) v="PRE-EXISTING (admin-merge + issue ladder)";;
    *)       v="NEW-CHECK (branch-added; investigate)";;
  esac
  printf "%-40s main=%-10s -> %s\n" "$chk" "${s:-not-run}" "$v"
done
```

#### 2. Rule out status-rollup artifacts (cancelled / superseded / stale-cache)

A red rollup is often NOT a real failure. The rollup mixes runs from ALL of the PR's commits.

**Force-push cancelled runs (Trigger 1).** After `git push --force-with-lease` (e.g. post-rebase),
GHA marks in-flight runs on the prior SHA `CANCELLED`; they render red next to the new SHA's
runs. On Odyssey PR #5380, all 50+ "failures" were `CANCELLED` from the rebased-out SHA;
the tip had zero `FAILURE`. Filter by tip SHA:

```bash
TIP=$(gh pr view <PR> --json headRefOid --jq .headRefOid)
gh run list --branch <branch> --limit 60 --json conclusion,headSha \
  | jq --arg s "$TIP" '[.[]|select(.headSha==$s)]|group_by(.conclusion//"queued")
       |map({key:(.[0].conclusion//"queued"),count:length})'
```

After a force-push, GHA auto-schedules fresh runs on the new SHA — no manual rerun needed.

**Concurrency supersession (Trigger 2, verified-ci).** Without any force-push, a higher-priority
queued run cancels an in-flight rerun. On Hephaestus PR #1073, `gh pr checks` summarized "4 fail"
after `gh run rerun --failed`; all four were CANCELLED mid-run with
`Canceling since a higher priority waiting request for required-Required Checks-<branch> exists`
/ `The operation was canceled.`, with zero `FAILED`. Verify against the LATEST run:

```bash
gh run list --branch <branch> --limit 3                       # newest is authoritative
gh run view --log --job=<jobid> | grep -c 'FAILED'            # 0 => supersession artifact
gh run view --log --job=<jobid> | tail -n5                    # ends "The operation was canceled."
```

**Stale CI cache (verified-ci).** A required check (e.g. `security/dependency-scan`) failing
*identically across multiple unrelated branches incl. main* with a clean diff = repo-wide infra,
not your code. Fingerprint: the gate log *installs* the fixed version while pip-audit *reports*
the old vulnerable one (poisoned `.pixi`/setup-pixi cache). Trust a LOCAL run over stale CI:

```bash
grep -n "urllib3" pixi.lock | head        # lockfile already pins the fix (2.7.0)
pixi run -e lint pip-audit                 # -> "No known vulnerabilities found"
git log origin/main --oneline | grep -iE "unblock CI|cache poison|\.pixi cache"
gh pr update-branch <N>                    # pull the cache-invalidation fix from main (no diff change)
gh api repos/$ORG/$REPO/commits/<merge-sha> --jq '.commit.verification.verified'  # true => signed-gate ok
```

Heuristic table:

| Indicator | Meaning |
|---|---|
| `mergeable: MERGEABLE` + `BLOCKED` + `real_failures: []` | Healthy; blocked only on queued/in-progress |
| `mergeable: CONFLICTING` + `DIRTY` | Real conflict — rebase needed |
| `mergeable: MERGEABLE` + `BLOCKED` + `real_failures: [...]` | Real failures — investigate |
| Many `CANCELLED` on a non-tip SHA | Stale from force-push — ignore |

#### 3. Check main-branch history (systemic vs PR)

For each failing workflow, read recent main conclusions:

```bash
gh run list --branch main --limit 10 --workflow "<Workflow>" \
  --json conclusion,createdAt,headSha \
  --jq '.[] | "\(.createdAt)\t\(.conclusion)\t\(.headSha[0:8])"'
```

3+ consecutive `failure` on main → **SYSTEMIC** (stop bisecting). Mixed → flaky pre-existing
if the failing files are unrelated to the diff. All `success` → potentially PR-introduced.
Do this per distinct workflow — they can be in different states. On Odyssey PR #5381, the
`execution crashed` failure had 7+ consecutive main failures → addressed in a separate
workaround PR #5382, not the surface PR.

#### 4. Classify flaky / infra signatures (before any rerun)

| Signature in log | Classification | Action |
| --- | --- | --- |
| `HTTP 5xx` on `git fetch` / `actions/checkout` / `upload-artifact` | GitHub infra flake | Leave; next push re-runs. Do NOT `gh run rerun`. |
| `mojo: error: execution crashed` + `libKGENCompilerRTShared.so`, no Mojo frame | libKGEN JIT crash (modular#6413) | Reference upstream; do NOT revert the Mojo bump; workaround in a separate PR |
| `SIGABRT` in a test file NOT in the PR diff, passes on main | Pre-existing Mojo flake | Confirm via main history; do not fix in PR |
| `Cannot connect to podman socket` | Container setup race | Leave / file infra issue |
| `fortify_fail_abort` only inside a docstring / commit body | grep text-match noise | Ignore — not a real abort |
| `error: compilation failed` / test-specific assert in a file the PR touched | PR-introduced regression | Fix the PR |

ProjectOdyssey hard policy: NEVER `gh run rerun` to dismiss a failure as a flake; NEVER
revert/pin-back a Mojo version bump; ALWAYS file/reference a Modular issue for runtime crashes
and fix forward. Note `gh pr checks --json` has a narrow schema — valid fields are
`bucket,completedAt,description,event,link,name,startedAt,state,workflow`; there is NO
`status`/`conclusion`/`required`. Requesting a bad field makes gh exit non-zero on EVERY call;
classify such deterministic CLI-arg errors as fail-fast (one wrong field once tripped a
`gh_cli` circuit breaker and bricked a 10-item batch).

#### 5. Stale duplicate-commit detection (all sanitizers fail identically)

When asan+tsan+ubsan+lsan (or every compilation job) fail the SAME test identically, suspect a
logical error from a stale parallel-attempt commit, not a data race (races show under TSan only):

```bash
git fetch origin
git log --oneline origin/main..origin/<branch>          # MORE commits than the PR claims?
gh pr list --state all --search "<symbol from suspicious commit>"   # already merged elsewhere?
# Rebuild with only the real payload (do NOT amend — that edits the wrong commit):
git checkout -B <branch> origin/main
git cherry-pick <real-payload-sha>
git push --force-with-lease origin <branch>             # bare --force is blocked by Safety Net
```

On Keystone PR #436, stale commit `984fef0` duplicated a fix already on main via PR #435;
rebuilding with only the real payload restored green. C++ pitfall in such stale fixes:
`return const std::vector<T>&` under a `lock_guard` is always wrong (lock released at return →
dangling ref); return by value.

#### 6. Stacked / rebased PR series

When earlier PRs in a stack merged but later ones are behind main, rebase first, then map logs:

| Log Output | Root Cause | Fix |
| --- | --- | --- |
| `stat .../Containerfile: no such file` | Predecessor not merged | Rebase onto main |
| `[org] is an organization. License key is required` | `gitleaks-action@v2` needs paid license | Replace with gitleaks CLI |
| `failed to resolve source metadata ... not found` | Stale pinned image digest | Pull fresh linux/amd64 digest |
| `Expected exactly N FROM lines ... found N+1` | Test asserts old Dockerfile structure | Update stage-count test |
| `AttributeError: module ... has no attribute 'old_name'` | Test patches a function the PR renamed | `@patch` the NEW inner function |

Resolve YAML conflicts (composite action vs inline steps) with Python `str.replace()`, never
sed/heredoc — `${{ }}` expressions corrupt under shell interpolation. Verify fix commit reached
remote (`git log --oneline origin/<branch>...<branch>`); a force-push may have dropped it.

#### 7. Surface stale-pattern / coverage warnings in the PR comment

Diagnostic CI output buried in stderr never reaches reviewers. To surface stale CI-group
warnings, add `stale_patterns: Optional[List[str]] = None` to `generate_report()`, append a
`### Stale CI Patterns` section when non-empty (after both uncovered/covered branches, before
`return`), and widen the post guard to `if post_pr and (uncovered or stale_patterns):` —
**parenthesize**, since `and` binds tighter than `or`. For the coverage gate, note it can
measure the merge-preview tree rather than the branch alone, producing a discrepancy that is
not a PR regression — diagnose with main history before "fixing".

#### 8. Post-rebase recovery when CodeQL and validate fail independently

After a feature branch is rebased onto the default branch, treat each red gate as an independent
failure until proven otherwise. A CodeQL fix does not imply validate is fixed, and a local pytest
pass does not prove CI validate will pass if tests depend on CI-only filesystem state.

1. Resolve rebase conflicts, then continue noninteractively in automation if Git opens an editor:

   ```bash
   git -c core.editor=true rebase --continue
   ```

2. Push the rebased branch and collect the current PR state:

   ```bash
   gh pr checks "<pr>" --repo "<owner>/<repo>"
   gh pr view "<pr>" --repo "<owner>/<repo>" \
     --json mergeStateStatus,mergeable,headRefOid,url
   ```

3. For CodeQL/GitHub Advanced Security failures, remember that the identifier from `gh pr checks`
   may be a check-run id, not a workflow run id. Use the check-runs and code-scanning APIs to read
   the rule id, path, line, and alert state.

4. For validate failures where local tests pass, inspect whether tests are touching host-specific
   filesystem probes, auto-discovered cluster/container paths, or other ambient CI state. Make tests
   deterministic by patching the probe or passing explicit CLI configuration in the test. Do not add
   environment-variable runtime config solely to make tests pass when the product direction forbids
   env-based configuration.

5. After each fix, push and poll `gh pr checks`. The final gate is: CodeQL green, validate green,
   security/SCA green, branch clean, and `gh pr view` reports mergeable/current `headRefOid`.

#### 9. Resolve

- **PR-INTRODUCED** → fix in this PR (your responsibility).
- **PRE-EXISTING** → ladder, in order: (A) quick fix only if ≤10 min and no scope creep;
  (B) admin-merge `gh pr merge <PR> --repo <org/repo> --squash --admin` (needs admin scope;
  if absent, auto-merge stays armed for a human); (C) ALWAYS file a tracking issue (even with
  A/B). Never expand PR scope to fix unrelated rot.
- **Systemic / infra flake / cache** → leave the surface PR; link the tracking PR/issue,
  `gh pr update-branch` if main is already fixed; do not rerun/revert.
- **No-op** → if all failures are confirmed pre-existing, enable auto-merge
  (`gh pr merge <PR> --auto --rebase`) and STOP. Do NOT create empty commits, manufacture
  changes, run passing tests locally, or commit `.claude-review-fix-*.md` artifacts.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Trusting a reviewer's `PREEXISTING_CI_NOISE` label | Took the classification at face value (Agamemnon #368, Hermes #614) | `check-runs` API showed those checks PASSED on main HEAD — failures were PR-introduced | ALWAYS re-verify with `check-runs` on main HEAD; ~5 sec vs ~10 min wasted per false trust |
| Comparing the workflow's overall conclusion | Used the workflow `conclusion` instead of the individual required-check `name` | A workflow can show FAILURE while its required sub-job PASSED | Key the `check-runs` query on the EXACT `name` from `statusCheckRollup` |
| File-overlap heuristic alone | Assumed zero diff-overlap means pre-existing | A check can fail from env/config drift unrelated to file paths | File overlap is a hint; the check-runs API on main HEAD is the only authoritative test |
| Reading "50+ failed checks" in the UI as real | Assumed real test failures post-rebase | Most entries were `CANCELLED` from the force-pushed-away SHA, not `FAILURE` | The rollup mixes runs from ALL of the PR's commits; filter by tip SHA |
| Reading `gh pr checks` "N fail" as real after a rerun | Treated 4 "fail" as failures (Hephaestus #1073) | Jobs were CANCELLED by concurrency supersession; 0 `FAILED`, latest run succeeded | A "fail" in `gh pr checks` can be a superseded run; verify against the latest run + grep log for `FAILED` |
| Bisecting the PR diff before checking main | Started bisecting a red workflow | 7+ consecutive main runs had the same failure — it was systemic | Run `gh run list --branch main` FIRST; 3+ consecutive failures = systemic, stop |
| `gh run rerun --failed` to "see if it's a flake" | Considered rerunning crashed Mojo jobs | Violates the no-CI-retries policy; masks systemic upstream bugs, no diagnostic value | Root-cause the signature (libKGEN→modular#6413), reference upstream, workaround in a separate PR |
| Proposing to revert the Mojo version bump | JIT crash appeared after the bump | Reverting hides the bug upstream and traps the repo on an old toolchain | Fix forward: file/reference the Modular issue, add a CI-side workaround, keep the bump |
| Treating an all-sanitizer failure as a data race | Wrote a fresh TSan synchronization fix | Identical failures across asan/tsan/ubsan/lsan = logical UB; the fix already landed on main | `gh pr list --state all --search "<symbol>"` before writing a fix; cherry-pick only the real payload |
| `git commit --amend` on the stale commit | Tried to correct it in place | Edits the wrong commit and rewrites history confusingly | Rebuild from fresh `origin/main` and cherry-pick only the real payload — cleaner, auditable |
| Trying to fix urllib3 in the blocked PR | Bumped/pinned to satisfy pip-audit | `pixi.lock` already pinned the fix and local pip-audit passed — it was a stale CI cache | Trust a local run over stale CI; install-vs-report version contradiction = cache poisoning; rebase via `gh pr update-branch` |
| Creating an empty/trivial commit | `git commit --allow-empty` to satisfy "implement all fixes" | Pollutes history; the plan said no action needed | Never manufacture work; if confirmed pre-existing, enable auto-merge and stop |
| Combined guard `if post_pr and uncovered or stale_patterns:` | Relied on default precedence | `and` binds tighter than `or`, so the stale arm ran unconditionally | Parenthesize mixed `and`/`or`: `if post_pr and (uncovered or stale_patterns):` |
| `gh pr checks --json name,status,conclusion,...` | Requested fields that don't exist on that subcommand | gh rejected the whole call (`Unknown JSON field: "status"`) non-zero; retried as transient, tripped a circuit breaker | Valid fields are `bucket,...,state,workflow`; classify deterministic CLI-arg errors fail-fast, never retry |
| Letting rebase continue open an editor in automation | Ran plain `git rebase --continue` after resolving conflicts | Git tried to launch an editor for the commit message and blocked the automated session | Use `git -c core.editor=true rebase --continue` |
| Treating local pytest pass as enough for validate | Fixed tests locally and assumed CI validate would match | CI had different filesystem auto-detection inputs, so the validate job still failed | Patch probes or pass explicit CLI config in tests so CI and local runs exercise deterministic inputs |
| Using environment variables to hide auto-detection drift | Proposed env-based runtime configuration just for tests | The product contract forbade env-based runtime config, and envs would mask the real deterministic-test gap | Keep runtime config explicit; tests should patch filesystem probes or pass CLI options |
| Treating CodeQL green as PR-ready | Fixed security alerts and stopped polling | Validate was an independent gate and still red | Poll all required gates after each push and confirm mergeability/head SHA before declaring ready |

## Results & Parameters

### Signature → classification map

| Log signature | Tag | Tracking |
| --- | --- | --- |
| `HTTP 5xx` on fetch/checkout | infra-flake | GitHub status |
| `mojo: error: execution crashed` + `libKGENCompilerRTShared.so` | mojo-jit | modular/modular#6413 |
| Podman socket connect refused | container-setup | repo infra |
| `fortify_fail_abort` in narrative text | noise | ignore |
| Same check red on multiple unrelated branches, install≠report version | stale-cache | cache invalidation on main |
| Test file outside diff, reproducible on main | systemic | link main run / tracking issue |
| Test file inside diff, reproducible locally | pr-regression | fix the PR |

### Decision rule (one-liner)

> If `gh run list --branch main` shows 3+ consecutive `failure` for the same workflow, OR the
> same required check is red on unrelated branches, the failure is NOT the PR's — do not blame,
> rerun, revert, or bisect; use the admin-merge + tracking-issue ladder or `gh pr update-branch`.

### Tracking issue body template

```markdown
## Failing check
`<exact check name from statusCheckRollup>`
## Status on main
- Main HEAD SHA: <sha>  | Conclusion: failure | First observed: <date/run URL>
## Log excerpt
<root-cause lines>
## Suspected root cause
<one paragraph>
## Action checklist
- [ ] Reproduce on main  - [ ] Identify regressing commit  - [ ] Open fix PR  - [ ] Close when green
```

### Empirical re-classification rate (2026-05-11 sweep)

3 of 3 lingering BLOCKED PRs needed this triage; 2 of 3 reviewer `PREEXISTING_CI_NOISE` labels
were wrong. Diagnose with the check-runs API every time before fixing or admin-merging.

### Retrigger flaky CI (only after classifying as flake)

```bash
gh pr diff <pr> --name-only          # confirm failing files are NOT in the diff
gh run rerun <run-id> --failed       # --failed: only failed jobs, not the whole workflow
```

### Post-rebase gate checklist

```bash
gh pr checks "<pr>" --repo "<owner>/<repo>"
gh pr view "<pr>" --repo "<owner>/<repo>" \
  --json mergeStateStatus,mergeable,headRefOid,url
git status --short
```

Expected final state: CodeQL passes, validate passes, dependency/security analysis passes, branch
has no local changes, `mergeable` is clean, and `headRefOid` matches the pushed fix commit.

## Verified On

| Project | Context | Details |
| ------- | ------- | ------- |
| ProjectOdyssey | PR #5380 post-rebase showed 50+ "failures" — all `CANCELLED` from the prior SHA (force-push, Trigger 1) | Filtering by tip SHA avoided a wasteful rerun (verified-local) |
| ProjectOdyssey | PR #5381 `execution crashed` had 7+ consecutive main failures (modular#6413) | Addressed in separate workaround PR #5382, not the surface PR (verified-ci) |
| ProjectHephaestus | PR #1073 `gh pr checks` "4 fail" after `gh run rerun --failed` | All four CANCELLED by concurrency supersession; latest run succeeded (verified-ci) |
| ProjectHephaestus | PRs #1019/#1022/#1024 `security/dependency-scan` red on every branch (urllib3 stale `.pixi` cache) | Lockfile already pinned 2.7.0; unblocked via `gh pr update-branch` after #1021 cache fix (verified-ci) |
| ProjectAgamemnon | PR #368 markdownlint MD031 + trivy mislabeled `PREEXISTING_CI_NOISE` | check-runs API showed PR-introduced — fixed in PR (verified-ci) |
| ProjectHermes | PR #614 urllib3 CVE mislabeled `PREEXISTING_CI_NOISE` | check-runs API showed PR-introduced — upgraded urllib3 (verified-ci) |
| ProjectKeystone | PR #552 `coverage` truly pre-existing (`BackpressureConcurrentTrigger` aborts on main) | Admin-merged + tracking issue #553 (verified-ci) |
| ProjectKeystone | PR #436 all 4 sanitizers failing `AsyncAgentsConcurrentProcessing` identically | Stale duplicate commit `984fef0` (fix already on main via #435); rebuilt with real payload only (verified-local) |
| Sanitized PR session | Post-rebase CodeQL and validate remediation | CodeQL, validate, security/SCA, and analysis gates green; branch clean and mergeable (verified-ci, 2026-06-19) |
