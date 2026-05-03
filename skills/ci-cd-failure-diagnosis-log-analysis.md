---
name: ci-cd-failure-diagnosis-log-analysis
description: "Diagnose CI failures by reading logs, identifying error patterns, and classifying root causes. Use when: (1) CI pipeline fails and you need to understand why, (2) tests pass locally but fail in CI, (3) multiple unrelated checks fail simultaneously, (4) CI retry logic labels failures as JIT crashes, (5) need to distinguish Mojo JIT crashes from real compile/test errors, (6) CI fails on a PR but PR changes look unrelated to failures, (7) docs-only or cleanup PRs show red CI, (8) multiple batch PRs all show BLOCKED status, (9) need to decide whether to block merge or proceed, (10) adding or auditing lint/format enforcement jobs to GitHub Actions workflows, (11) cross-repo conflict resolution on rename/refactor PRs, (12) CI-only crashes caused by debug_assert or JIT compilation overhead in Mojo, (13) enforcing required status checks across a GitHub organization, (14) triaging flaky CI failures to separate infrastructure issues from deterministic bugs, (15) fixing justfile build recipes that silently skip library validation, (16) standardizing default branches and fixing broken CI across multiple repos, (17) fixing pre-commit failures from mypy/ruff/coverage issues on cross-Python-version packages, (18) promoting monolithic CI matrix groups to per-subdirectory auto-discovery entries, (19) fixing CI workflows with missing pip dependency installs, (20) optimizing CI wall-clock time via runner pinning and changed-files-only pre-commit, (21) Dependabot PRs conflict after other Dependabot PRs merge to main, (22) gh pr merge fails with squash or merge-commit in rebase-only repos, (23) multiple Dependabot dependency bumps are open and landing sequentially, (24) CodeQL alert flags a workflow for lacking a permissions block, (25) Angular/Karma workflow fails because GitHub Actions runner Chrome sandboxing is inconsistent, (26) CI checks packaged web assets after a rebuild and hashed bundle filenames make git diff gates brittle."
category: ci-cd
date: 2026-03-28
version: "3.0.0"
user-invocable: false
verification: unverified
tags:
  - ci-failure
  - flaky-tests
  - mojo-jit
  - batch-pr
  - diagnosis
  - pre-existing
  - dependabot
  - conflict
  - rebase
  - codeql
  - permissions
  - karma
  - playwright
  - chromium
  - frontend
  - pipeline-maintenance
---

# CI Failure Diagnosis, Log Analysis, and Pipeline Maintenance

## Overview

| Date | Objective | Outcome |
| ------ | ----------- | --------- |
| 2026-03-28 | Consolidated diagnosis and log-analysis knowledge for CI failures | Operational |
| 2026-04-12 | v2.0.0: Absorbed pre-existing failure triage, batch PR diagnosis, and crash decision tree | Merged |
| 2026-05-03 | v3.0.0: Absorbed 5 additional skills — pipeline maintenance patterns, Dependabot conflict resolution, CodeQL permissions fix, Karma/Playwright Chromium launcher, and packaged frontend functional asset validation | Merged |

Absorbed: ci-cd-pipeline-maintenance-patterns, ci-cd-dependabot-conflict-resolution-pattern, ci-cd-codeql-missing-workflow-permissions-fix, ci-cd-karma-playwright-chromium-launcher, ci-cd-packaged-frontend-functional-asset-validation on 2026-05-03

Systematic approach to reading CI logs, identifying error patterns, classifying failure types
(PR-caused vs pre-existing vs flaky), and diagnosing root causes before attempting fixes.
Covers single-PR diagnosis, batch PR diagnosis across many PRs, the decision tree for
distinguishing infrastructure crashes from real regressions, pipeline maintenance patterns,
Dependabot conflict resolution, CodeQL permissions fixes, Karma/Playwright Chromium setup,
and packaged frontend functional asset validation.

## When to Use

- CI pipeline fails and you need to understand why
- Analyzing test failure logs from GitHub Actions
- Extracting error messages from build artifacts
- Identifying patterns in recurring failures
- Determining if failure is environmental or code-related
- Tests pass locally but fail in CI (especially when CI uses `--Werror`)
- Multiple unrelated-looking checks fail simultaneously
- A check that passed on the previous run now fails with identical code
- Mojo runtime crashes (`error: execution crashed`) appear in CI
- CI retry logic labels failures as "Mojo JIT crash" — verify before trusting
- CI tests fail and retry logic labels them as "likely Mojo JIT crash" but tests pass locally
- `execution crashed` is assumed but never actually appears in CI logs
- Deprecation warnings exist in the codebase and CI uses `--Werror`
- CI fails on a PR but PR changes look unrelated to failures
- PR only changes documentation/config (no code) and CI test failures involve runtime crashes
- Need to decide whether to block merge or proceed on red CI
- Suspecting flaky or pre-existing infrastructure failures
- Multiple batch PRs all show BLOCKED merge status
- Mojo tests crash with "execution crashed" or "libKGENCompilerRTShared.so" errors
- GitHub Actions fail with HTTP 429 (rate limiting) or HTTP 500 (CDN outage)
- Repository has ruff/lint rules but no CI enforcement, or pre-commit hooks can be bypassed
- A rename/refactor PR shows CONFLICTING merge state after main advances
- Tests pass locally but CI crashes with `execution crashed` / `libKGENCompilerRTShared.so` after adding `debug_assert` to `@always_inline` methods
- Multiple repos in an org lack branch protection or required status checks
- A `just build` recipe silently excludes important source directories from compilation
- Repos have inconsistent default branch names (master vs main) and CI never triggers
- mypy reports `Unused "type: ignore"` on CI but the ignore is needed locally; or ruff/coverage failures after adding new modules
- A single CI matrix group covers multiple subdirectories via compound patterns and silently misses new files
- A GitHub Actions workflow fails with `ModuleNotFoundError` for a Python package
- CI is too slow: `ubuntu-latest` causes cache invalidation, pre-commit runs on all files, Dockerfile reinstalls dependencies
- Dependabot PRs are stacking and one shows CONFLICTING/DIRTY after others have merged
- `gh pr merge --squash` or `gh pr merge --merge` returns "Repository does not allow..." error
- A GitHub issue was filed as an audit/batch tracker — check if sub-issues already resolved before acting
- Test file has ruff E402 (module-level import not at top of file) and conftest.py already sets `sys.path`
- A GitHub CodeQL code scanning alert fires `actions/missing-workflow-permissions` on a workflow file
- A workflow lacks an explicit `permissions:` block (leaving the default `GITHUB_TOKEN` with broad write access)
- An Angular/Karma workflow fails because GitHub Actions runner Chrome sandboxing or browser discovery is inconsistent
- CI checks packaged web assets after a rebuild with hashed bundle filenames causing git diff gate failures

## Verified Workflow

### Quick Reference

```bash
# View PR checks
gh pr checks <pr-number>

# Get failed logs only
gh run view <run-id> --log-failed

# Download CI logs from artifact
gh run download <run-id> -D /tmp/ci-logs

# Extract from workflow run
gh run view <run-id> --log > /tmp/ci-output.log

# Grep for error patterns
grep -i "error\|failed\|panic\|exception" /tmp/ci-output.log

# Get summary of failures
tail -100 /tmp/ci-output.log | grep -A 5 "FAILED\|ERROR"

# Get error details for a specific job
gh run view <run-id> --repo <owner>/<repo> --log-failed 2>&1 | grep -E "error:|FAIL|❌" | head -30

# Check main branch CI history
gh run list --branch main --limit 5
gh run list --branch main --workflow "<Workflow Name>" --limit 3

# Bulk status check across multiple PRs
for pr in 5082 5083 5084; do
  echo "=== PR #$pr ==="
  gh pr checks $pr 2>&1 | grep -E "fail"
done

# Check merge state of all PRs
gh pr list --state open --json number,mergeStateStatus

# Re-run only failed jobs
gh run rerun <run-id> --repo <owner>/<repo> --failed

# Monitor until completion
gh run watch <run-id> --repo <owner>/<repo> --exit-status
```

### Phase 1: Collect and Extract Logs

1. **Get PR check status**
   ```bash
   gh pr checks <PR_NUMBER>
   ```
   Identifies which checks are failing and provides direct links to logs.

2. **View detailed logs**
   ```bash
   gh run view --job=<JOB_ID> --log
   ```
   Downloads complete CI logs for analysis.

3. **Extract error messages**
   ```bash
   gh run view --job=<JOB_ID> --log | grep -E "FAILED|ERROR|error" | head -20
   ```
   Quickly surfaces actual failure points.

4. **Search for specific error context**
   ```bash
   gh run view --job=<JOB_ID> --log | grep -B 10 -A 10 "<error_message>"
   ```
   Gets surrounding context for error understanding.

### Phase 2: Classify the Failure Type

**Error category patterns**:

| Category | Look For | Check |
| ---------- | ---------- | ------- |
| Compilation Errors | `error:`, `undefined`, `type mismatch` | Mojo/Python syntax, imports, type annotations |
| Test Failures | `FAILED`, `AssertionError`, `ValueError` | Test logic, expected vs actual values |
| Timeout Issues | `timeout`, `timed out`, `hanging` | Long-running loops, infinite recursion |
| Dependency Issues | `not found`, `import failed`, `version conflict` | Package versions, environment setup |
| Environmental Issues | `permission denied`, `out of memory`, `disk full` | Resource limits, configuration |
| JIT Crashes | `execution crashed`, `libKGENCompilerRTShared.so` | Non-deterministic Mojo compiler crash |
| Compile Errors (--Werror) | `'alias' is deprecated`, `unused return value` | Mojo deprecation promoted to error |
| Transient Infrastructure | HTTP 429, HTTP 500 | External service rate limiting or CDN outage |
| Infrastructure | `504 Gateway Time-out`, `Cache not found`, container build failure | Fix CI config |
| Deterministic bug | `failed to parse`, `error:` with line number, assertion failure | Fix code |

### Phase 3: Classify as PR-Caused, Pre-Existing, or Flaky

#### Step 3a: Identify Changed Files

Understand the PR scope before investigating failures:

```bash
# All changed files
git diff main...HEAD --name-only

# Check if any source files were changed
git diff main...HEAD --name-only | grep -E "\.(mojo|py)$"

# Confirm no Mojo code was changed (for non-code PRs)
git diff main...HEAD -- '*.mojo'
# Empty output confirms no logic changes
```

#### Step 3b: Classify by Changed File Type

| File Type | Can Cause |
| ----------- | ----------- |
| `.claude/agents/*.md`, `agents/*.md`, `*.md` only | Documentation only — cannot cause Mojo runtime crashes |
| `.mojo`, `.🔥`, `shared/`, `tests/` | Can cause test failures |
| `.github/workflows/` | Can affect CI infrastructure |
| `requirements.txt`, `pixi.toml` | Can cause pip install / dependency failures |

**Config/docs PRs** with Mojo test failures = flaky (JIT crashes).
**PRs with pip/dependency errors** = real failures from the PR's changes.
**HTTP 429/500 errors** = transient GitHub infrastructure.

#### Step 3c: Check Main Branch CI History

```bash
# Check recent runs of the failing workflow on main
gh run list --branch main --workflow "<Workflow Name>" --limit 5

# View a specific main run's failures
gh run view <run-id> --log-failed 2>&1 | head -100

# Confirm failure is pre-existing
gh run list --branch main --limit 5 --json name,conclusion
```

If all recent runs on `main` show `failure`, the failure is pre-existing.

#### Step 3d: Decision Table

| Changed files | Failing CI | Action |
| --------------- | ----------- | -------- |
| Only `.claude/`, `agents/`, docs | Mojo runtime crashes | Pre-existing — proceed |
| Only `.claude/`, `agents/`, docs | `link-check` on untouched files | Pre-existing — proceed |
| Only `.claude/`, `agents/`, docs | `pre-commit` / `test-agents` | PR-caused — fix required |
| Any `.mojo` / `shared/` / `tests/` | Any test failure | Investigate — may be PR-caused |
| `requirements.txt` / `pixi.toml` | pip ResolutionImpossible | PR-caused — fix dependency |

**Pre-existing only** → PR is ready to merge as-is.
**PR introduced failures** → fix before merging.

```bash
# Post to PR when confirmed pre-existing
gh issue comment <number> --body "All CI failures are pre-existing on main (confirmed via gh run list). PR only modifies documentation files. Safe to merge."
```

### Phase 4: Compare Failure Signatures

Do the failing test names match between PR and main?

- Same test groups failing (e.g., `Core DTypes`, `Data Loaders`, `Data Samplers`) → **pre-existing**
- New test groups failing that correspond to changed files → **PR-caused**

```bash
# Confirm no Mojo code was changed (for non-code PRs)
git diff main...HEAD -- '*.mojo'

# Check specifically for source files relevant to the failure
git diff main..<branch> --name-only | grep "\.mojo$"
git diff main..<branch> --name-only | grep "\.py$"
```

For batch PR diagnosis, find a "clean" PR (no code changes) as a baseline:

```bash
gh pr checks <CLEAN_PR_NUMBER> 2>&1 | grep -E "pass|fail"
gh pr diff <PR_NUMBER> --name-only
```

### Phase 5: Handle Mojo-Specific Failures

#### Check for --Werror Misattribution

Retry logic may mislabel compile errors as JIT crashes. **Always read the actual logs**:

```bash
gh run view <run-id> --log-failed 2>&1 | grep -E "error:|FAILED" | head -20
```

Look for **compile errors** (e.g., `'alias' is deprecated`) rather than `execution crashed`.

#### Reproduce Locally with CI Flags

```bash
# Match CI conditions exactly
pixi run mojo --Werror -I "$(pwd)" -I . tests/path/to/test.mojo
```

#### Find All Deprecated Syntax

```bash
grep -rn "^alias " --include="*.mojo" shared/ tests/
```

#### Identify Flaky Runtime Crashes

Mojo runtime crashes (`error: execution crashed`) in CI are often non-deterministic:
- Not reproducible locally (environment-specific)
- Not correlated with code changes in your PR
- Can be marked `continue-on-error: true` in CI matrix

**Runtime crash signatures:**
- `error: execution crashed` — Mojo runtime segfault, usually in `libKGENCompilerRTShared.so`
- Stack traces with only library frames (no user code) — infrastructure issue
- Crash before any test output — crash in static initialization

**Introduced regression signatures:**
- `error: compilation failed` — code broke the build
- Test-specific failure messages — code logic is wrong
- Crash only in tests that directly call new methods

Key question: **Do the failing test groups cover files touched by the PR?**

```bash
# See what the PR actually changed
git show <commit-hash> --stat

# For each failing test group, check what test files it covers
grep -A3 '"<Failing Job Name>"' .github/workflows/comprehensive-tests.yml
```

If failing jobs test files completely unrelated to the PR diff → strong flakiness signal.

#### Diagnose debug_assert JIT Compilation Overhead

When `debug_assert` is added to `@always_inline` methods and CI starts failing with mass `execution crashed`, but tests pass locally:

1. Count call sites that inline the modified method: `grep -rn "\.load\[DType\.\|\.store\[DType\." shared/ --include="*.mojo" | wc -l`
2. Compare failing jobs vs main's failing jobs — zero overlap means it's your regression
3. Distinguish from pre-existing failures: `gh api repos/<owner>/<repo>/actions/runs/<run_id>/jobs --jq '.jobs[] | select(.conclusion == "failure") | .name' | sort`
4. Fix: remove `debug_assert` from `@always_inline` methods. The method body becomes a pure pass-through:
   ```mojo
   @always_inline
   fn load[dtype: DType](self, index: Int) -> Scalar[dtype]:
       return self._data.bitcast[Scalar[dtype]]()[index]
   ```

**Why it works locally but fails in CI**: Fresh JIT cache + Docker container environment + concurrent compilation pressure pushes total compilation footprint past the internal JIT buffer overflow threshold. The crash signature is `libc.so.6+0x45330` (fortify_fail_abort).

#### Compare Against Last Successful Main Run

```bash
# Find recent main branch runs
gh run list --branch main --workflow "Comprehensive Tests" --limit 5 --json conclusion,databaseId

# Check job statuses on the most recent SUCCESSFUL main run
gh run view <successful-main-run-id> --json jobs 2>&1 | python3 -c "
import json, sys
data = json.load(sys.stdin)
for job in data.get('jobs', []):
    print(f'{job.get(\"conclusion\", \"N/A\")}: {job[\"name\"]}')
" | grep -E "failure|<Failing Job Name>"
```

If the same jobs PASSED on main recently → our PR is a candidate. If they also failed on
main → pre-existing issue.

### Phase 6: Re-run Flaky Failures

```bash
# Re-run only the failed jobs (not the whole workflow)
gh run rerun <run-id> --repo <owner>/<repo> --failed

# Monitor until completion
gh run watch <run-id> --repo <owner>/<repo> --exit-status
```

**After re-run — interpret results:**
- Previously failing jobs now pass → **flaky CI**, no code fix needed
- Failures persist with same crashes → **investigate root cause** in PR changes
- Only pre-existing failures remain (known broken tests on main) → **PR is clean**

**Check run conclusion before re-running** (cannot re-run in-progress runs):

```bash
CONCLUSION=$(gh run view <RUN> --json conclusion --jq '.conclusion')
if [ "$CONCLUSION" = "failure" ]; then
  gh run rerun <RUN> --failed
fi
```

### Phase 7: Validate Fix Didn't Break Unrelated Tests

The key question: **does the failure exist in commits on main that don't include your changes?**

```bash
# Check if error references a file you touched
gh run view <run-id> --repo <owner>/<repo> --log-failed 2>&1 | grep "error:" | grep -v "warning"
```

### Phase 8: Triage for Batch PRs

When reviewing many PRs simultaneously:

1. **Bulk status check**: Run `gh pr checks` across all PRs to get failure counts
2. **Identify baseline**: Find a PR that passes all checks (docs-only PRs are good baselines)
3. **Categorize failures** by checking what files each PR changes
4. **Get specific error messages**: Use `gh run view --log-failed` to extract actual errors
5. **Fix real failures**: Launch dedicated fix agent for the specific worktree
6. **Re-run flaky tests**: Use `gh run rerun <ID> --failed` for intermittent crashes
7. **Monitor re-runs**: Check status again after re-runs complete

```bash
# Get actual error from a failed job
JOB_ID=$(gh api repos/OWNER/REPO/actions/runs/<RUN>/jobs \
  --jq '.jobs[] | select(.conclusion=="failure") | .id')
gh api repos/OWNER/REPO/actions/jobs/$JOB_ID/logs | grep -B5 "error\|Error"
```

### Phase 9: CI Matrix Configuration for Persistent JIT Crashes

```yaml
matrix:
  test-group:
    - name: "Core Gradient"
      path: "tests/shared/core"
      pattern: "test_gradient*.mojo"
      continue-on-error: true  # Mojo JIT crash - see #<issue>
```

Then in the step: `continue-on-error: ${{ matrix.test-group.continue-on-error == true }}`

### Phase 10: Handle Flaky Link Checkers

```yaml
# In link-check.yml, exclude URLs with transient failures
args: --exclude conventionalcommits.org --exclude example.com
```

**Key distinction for link check failures**: Root-relative paths (`/path/...`) fail lychee; relative paths (`../path/...`) are fine.

### Phase 11: Verify Branch State

```bash
# Check branch is clean
git status

# Confirm PR scope
git log --oneline main..HEAD

# Confirm no broken references after deletions/renames
grep -rn "old-filename.md" . --include="*.md"
# Expected: no output

# Verify new links added in PR use relative paths
git diff main..<branch> -- "*.md" | grep "^+" | grep -o '([^)]*\.md)'
```

### Phase 12: For Docs-Only PRs — Run Pre-commit to Confirm

Even docs-only PRs can fail pre-commit if they introduce formatting issues:

```bash
pixi run pre-commit run --all-files 2>&1 | tail -20
```

Expected output: all hooks show `Passed`. The `mojo format` hook may emit GLIBC errors (environment incompatibility on local host) but still reports `Passed` — this is a known pre-existing environment issue, not a failure of the PR.

### Important Notes

- **Do NOT commit `.claude-review-fix-*.md` files** — these are temporary task instruction artifacts, not implementation files. Leave them as untracked.
- **Untracked files in `git status` are normal** after a no-op review fix.
- **GLIBC errors in pre-commit are environment noise** — look at per-hook status lines, not stderr noise.

---

## Pipeline Maintenance Patterns

### Quick Reference (Pipeline Maintenance)

```bash
# --- Ruff lint job: verify locally first ---
pixi run ruff check hephaestus scripts tests
pixi run ruff format --check hephaestus scripts tests
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/test.yml')); print('OK')"

# --- Cross-repo rename PR conflict resolution ---
git fetch origin && git checkout <branch> && git rebase origin/main
for f in $(git diff --name-only --diff-filter=U); do git checkout --theirs "$f" && git add "$f"; done
git rebase --continue
python3 scripts/validate_plugins.py
git push --force-with-lease
gh pr view <number> --json mergeStateStatus --jq '.mergeStateStatus'

# --- Diagnose Mojo CI-only crash (debug_assert + @always_inline) ---
grep -n "debug_assert" shared/tensor/any_tensor.mojo
grep -rn "\.load\[DType\.\|\.store\[DType\." shared/ --include="*.mojo" | wc -l

# --- Org-wide required checks audit ---
python3 scripts/audit_ci_status.py --runs 20
python3 scripts/enforce_required_checks.py --apply

# --- Flaky CI triage ---
gh run view <RUN_ID> --log-failed 2>&1 | grep -E "FAILED|execution crashed|error:|504|Cache not found" | head -40

# --- Justfile build validation ---
NATIVE=1 just check     # fast library type-check (no artifacts)
NATIVE=1 just ci-build  # full build: entry points + library packaging

# --- Branch rename (org-wide) ---
gh api --method POST repos/ORG/REPO/branches/master/rename --field new_name=main

# --- Pre-commit mypy fix: use importlib for version-dependent imports ---
# See detailed steps below

# --- Promote matrix subgroups ---
python3 scripts/validate_test_coverage.py

# --- Missing dependency in CI ---
grep -rl "script_name.py" .github/workflows/

# --- CI optimization: pin runners ---
for f in .github/workflows/*.yml; do sed -i 's/runs-on: ubuntu-latest/runs-on: ubuntu-24.04/g' "$f"; done
grep -rc "ubuntu-latest" .github/workflows/*.yml | grep -v ":0"
```

### Adding a Ruff Lint Job to CI

1. Verify codebase passes lint locally before modifying CI. If violations exist, fix them first in a separate commit.
2. Add a separate `lint` job to the existing test workflow. Use a separate job (not a step) so it runs in parallel with independent failure reporting.
3. Use a shorter timeout for the lint job (10 minutes vs 30 for tests).
4. Add workflow-level hardening if not already present: `concurrency` group with `cancel-in-progress: true`, `permissions: contents: read`.

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.head_ref || github.sha }}
  cancel-in-progress: true

permissions:
  contents: read

jobs:
  lint:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v6
      - name: Install pixi
        uses: prefix-dev/setup-pixi@v0.9.4
        with:
          pixi-version: v0.63.2
      - name: Cache pixi environments
        uses: actions/cache@v5
        with:
          path: |
            .pixi
            ~/.cache/rattler/cache
          key: pixi-${{ runner.os }}-${{ hashFiles('pixi.lock') }}
          restore-keys: |
            pixi-${{ runner.os }}-
      - name: Lint check
        run: pixi run ruff check hephaestus scripts tests
      - name: Format check
        run: pixi run ruff format --check hephaestus scripts tests
```

Quick reference for lint maintenance:

```bash
# --- Ruff lint job: verify locally first ---
pixi run ruff check hephaestus scripts tests
pixi run ruff format --check hephaestus scripts tests
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/test.yml')); print('OK')"
```

### Cross-Repo Rename PR Conflict Resolution

For rename/refactor PRs where all conflicts follow the same pattern (both sides changed the renamed text):

1. Fetch and rebase: `git fetch origin && git checkout <branch> && git rebase origin/main`
2. Check that all conflicts are homogeneous (same rename pattern): `git diff --name-only --diff-filter=U`
3. Batch-resolve with `--theirs` (the PR's renamed version):
   ```bash
   for f in $(git diff --name-only --diff-filter=U); do
     git checkout --theirs "$f" && git add "$f"
   done
   git rebase --continue
   ```
4. Validate repo integrity: `python3 scripts/validate_plugins.py`
5. Push and verify merge state: `git push --force-with-lease && gh pr view <number> --json mergeStateStatus --jq '.mergeStateStatus'`

For coordinating skill definition updates in a second repo after the rename, create an independent PR that references the original. Neither PR should block the other.

**Decision: When to use --theirs vs manual merge**
```text
Is the PR a rename/refactor where the intent is to change text references?
+-- YES: Are all conflicts in the renamed text (not structural changes)?
|   +-- YES -> Use --theirs for all conflicts (the rename IS the intent)
|   +-- NO  -> Manual merge for structural conflicts, --theirs for rename text
+-- NO -> Use standard conflict resolution (manual or --ours as appropriate)
```

### Org-Wide Required Status Checks Enforcement

1. **Audit all repos** (read-only): `python3 scripts/audit_ci_status.py --runs 20`
2. **Dry-run**: `python3 scripts/enforce_required_checks.py`
3. **Apply incrementally** — start with safest repo: `python3 scripts/enforce_required_checks.py --apply --repo ProjectScylla`
4. **Apply all**: `python3 scripts/enforce_required_checks.py --apply`
5. **Verify**: `python3 scripts/audit_ci_status.py --runs 5`

Key filtering rules for which jobs qualify as required checks:
- Minimum 3 executed runs (not skipped/cancelled)
- 100% pass rate
- Workflow triggers on `pull_request`
- No `paths:` filter on `pull_request` trigger (path-filtered jobs don't run on every PR)
- Exclude GitHub-automated jobs (Dependabot, CodeQL `Analyze` jobs)

GitHub API patterns:
```bash
# Repo has existing required checks (PATCH replaces entire list)
gh api --method PATCH repos/ORG/REPO/branches/BRANCH/protection/required_status_checks \
  --input - <<< '{"strict":false,"contexts":["existing","new-check"]}'

# Repo has no protection (PUT with full body)
gh api --method PUT repos/ORG/REPO/branches/BRANCH/protection \
  --input - <<< '{"required_status_checks":{"strict":false,"contexts":["check"]},"enforce_admins":false,"required_pull_request_reviews":null,"restrictions":null}'
```

### Flaky CI Root Cause Triage

For each failing test, classify into exactly one bucket before attempting any fix:

| Bucket | Signature | Action |
|--------|-----------|--------|
| **Infrastructure** | `504 Gateway Time-out`, `Cache not found`, container build failure | Fix CI config |
| **Deterministic bug** | `failed to parse`, `error:` with line number, assertion failure | Fix code |
| **Genuine JIT flake** | `execution crashed` with `libKGENCompilerRTShared.so`, NO test output before crash | Upstream Mojo bug |

```bash
# Full triage of a failed CI run
RUN_ID=<your-run-id>
gh run view $RUN_ID --log-failed 2>&1 | grep "❌ FAILED" | sort -u
gh run view $RUN_ID --log-failed 2>&1 | grep -E "504|Cache not found|Gateway" | head -5
gh run view $RUN_ID --log-failed 2>&1 | grep -E "failed to parse|error:.*line" | head -10
gh run view $RUN_ID --log-failed 2>&1 | grep "execution crashed" | head -5
```

**Docker Hub Thundering Herd fix** (replace Podman storage cache with image tar cache):
```yaml
- name: Cache container image tar
  uses: actions/cache@v5
  with:
    path: /tmp/podman-image-cache
    key: container-image-${{ hashFiles('Dockerfile', 'pixi.toml', 'pixi.lock') }}

- name: Load cached image or build
  run: |
    if [ -f /tmp/podman-image-cache/dev.tar ]; then
      podman load -i /tmp/podman-image-cache/dev.tar
    else
      podman compose build projectodyssey-dev
      mkdir -p /tmp/podman-image-cache
      podman save -o /tmp/podman-image-cache/dev.tar projectodyssey:dev
    fi
```

**Mojo syntax fixes for deterministic bugs**:
```mojo
# f-strings in function call arguments (parse error in Mojo)
# WRONG: assert_value_at(t, i, 1.0, message=f"t[{i}] should be 1.0")
# CORRECT:
assert_value_at(t, i, 1.0, message="t[" + String(i) + "] should be 1.0")

# Tuple destructuring (unknown declaration error)
# WRONG: var (a, b, c) = fn_returning_tuple()
# CORRECT:
var result = fn_returning_tuple()
var a = result[0]; var b = result[1]; var c = result[2]
```

### Justfile Build Validation Gaps

When `mojo build` is used for library code but library modules have no `fn main()`:

1. Fill empty `ci-build` recipe to run both entry-point compilation and library packaging:
   ```just
   ci-build:
       @just build ci
       @just package ci
   ```
2. Add `just check` recipe for fast developer feedback:
   ```just
   check:
       @just _run "just _check-inner"

   [private]
   _check-inner:
       #!/usr/bin/env bash
       set -euo pipefail
       REPO_ROOT="$(pwd)"
       OUT=$(mktemp -d)
       trap "rm -rf $OUT" EXIT
       pixi run mojo package --Werror -I "$REPO_ROOT" shared -o "$OUT/shared.mojopkg"
   ```
3. Update `validate` to delegate to `ci-build` — single source of truth.
4. Replace inline `mojo package` commands in CI YAML with `NATIVE=1 just ci-build`.

| Command | Requires main()? | Use For |
|---------|-------------------|---------|
| `mojo build` | Yes | Entry point binaries |
| `mojo package` | No | Library validation |

### Org-Wide Branch Rename and CI Fix

1. Identify repos needing rename:
   ```bash
   for repo in $(gh repo list ORG --no-archived --json name --jq '.[].name'); do
     branch=$(gh api repos/ORG/$repo --jq '.default_branch')
     if [ "$branch" != "main" ]; then echo "RENAME: $repo ($branch -> main)"; fi
   done
   ```
2. Rename via API (atomically updates default branch, PRs, and protection rules):
   ```bash
   gh api --method POST repos/ORG/REPO/branches/master/rename --field new_name=main
   ```
3. Fix self-hosted runner issues by switching to `ubuntu-latest` in workflow YAML.
4. Fix common broken workflow configs: remove invalid Semgrep `generateSarif: true` parameter; add `continue-on-error: true` to advisory security scans.
5. Re-audit and enforce: `python3 scripts/audit_ci_status.py --runs 20 --min-runs 1 && python3 scripts/enforce_required_checks.py --apply --remove-failing`

Use 4 worktree-isolated parallel agents for CI fixes across repos:
```python
Agent(isolation="worktree", run_in_background=True, prompt="Fix REPO CI...")
```

### Pre-Commit mypy / ruff / Coverage Fixes (Cross-Python-Version)

**mypy unused-ignore on version-dependent imports**: Use `importlib.import_module()` instead of `try/except import` with `type: ignore` comments:

```python
# WRONG: type:ignore breaks on Python 3.12 CI (tomllib in stdlib) but needed on 3.10
try:
    import tomllib  # type: ignore[no-redef]
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[no-redef]

# CORRECT: importlib avoids all type:ignore issues
import importlib
tomllib = None
for _mod_name in ("tomllib", "tomli"):
    try:
        tomllib = importlib.import_module(_mod_name)
        break
    except ModuleNotFoundError:
        continue
```

**Fix ruff issues in order**:
```bash
pixi run ruff format hephaestus/ tests/          # 1. Format first
pixi run ruff check . --select=F401,I001 --fix   # 2. Unused imports + sorting
pixi run ruff check . --select=RUF059 --fix --unsafe-fixes  # 3. Unused unpacked vars
pixi run ruff check . --select=C901              # 4. Check complexity manually
```

**Coverage gaps from main() functions** — add tests that monkeypatch `sys.argv`:
```python
class TestMain:
    def test_clean_returns_zero(self, tmp_path, monkeypatch):
        monkeypatch.setattr("sys.argv", ["cmd", "--repo-root", str(tmp_path)])
        assert main() == 0

    def test_stdin_input(self, monkeypatch):
        monkeypatch.setattr("sys.argv", ["cmd"])
        monkeypatch.setattr("sys.stdin", io.StringIO('{"data": []}'))
        assert main() == 0
```

Other ruff rules: N817 (CamelCase as acronym — rename `ET` to `ElementTree`); D301 (backslashes in docstrings — use `r"""`); SIM102 (collapse nested `if`).

### Promoting CI Matrix Subgroups for Auto-Discovery

Replace a monolithic CI matrix entry that uses compound patterns with per-subdirectory entries:

```yaml
# BEFORE (1 group — silently misses new subdirectory files)
- name: "Data"
  path: "tests/shared/data"
  pattern: "test_*.mojo datasets/test_*.mojo samplers/test_*.mojo transforms/test_*.mojo"

# AFTER (6 groups — each subdirectory auto-discovers test_*.mojo)
- name: "Data Core"
  path: "tests/shared/data"
  pattern: "test_*.mojo"
  continue-on-error: true
- name: "Data Datasets"
  path: "tests/shared/data/datasets"
  pattern: "test_*.mojo"
  continue-on-error: true
# ... one entry per subdirectory
```

Key insight: `Path.glob("dir/test_*.mojo")` is non-recursive — parent and subdirectory entries never overlap. Validate after editing: `python3 scripts/validate_test_coverage.py`.

### Missing Dependency in CI Workflow

1. Identify failure: `gh run list --branch main --limit 5` then `gh run view <run-id> --log-failed`
2. Find root cause: look for `ModuleNotFoundError` and the missing package name
3. Check sibling workflows: `grep -rl "script_name.py" .github/workflows/` — they likely already install the dependency
4. Add install step between "Set up Python" and the script execution step:
   ```yaml
   - name: Install dependencies
     run: pip install <missing-package>
   ```
5. Submit via PR — do NOT commit regenerated output files alongside the fix.

### CI Optimization (Runner Pinning, Changed-Files Pre-commit, Dockerfile)

**Pin all runners to avoid cache invalidation**:
```bash
for f in .github/workflows/*.yml; do
  sed -i 's/runs-on: ubuntu-latest/runs-on: ubuntu-24.04/g' "$f"
done
grep -rc "ubuntu-latest" .github/workflows/*.yml | grep -v ":0"  # Should be empty
```

**Changed-files-only pre-commit for PRs**:
```yaml
- name: Run pre-commit hooks
  env:
    EVENT_NAME: ${{ github.event_name }}
    BASE_REF: ${{ github.base_ref }}
  run: |
    if [ "$EVENT_NAME" = "pull_request" ]; then
      git fetch origin "$BASE_REF" --depth=1
      SKIP=mojo-format pixi run pre-commit run --from-ref "origin/$BASE_REF" --to-ref HEAD --show-diff-on-failure
    else
      SKIP=mojo-format pixi run pre-commit run --all-files --show-diff-on-failure
    fi
```

Always use `env:` to capture `github.event_name` and `github.base_ref` — never inline `${{ }}` expressions in `run:` commands (workflow injection security check).

**Dockerfile multi-stage: copy .pixi instead of reinstalling**:
```dockerfile
# Runtime stage — copy from builder, don't reinstall
COPY --from=builder /root/.pixi /root/.pixi
COPY --from=builder /build/.pixi /app/.pixi
COPY pixi.toml pixi.lock ./
# Remove curl from apt-get (no longer needed for pixi installer)
```

---

## Dependabot Conflict Resolution

### Quick Reference (Dependabot)

```bash
# Determine repo merge policy
gh api repos/<owner>/<repo> --jq '.allow_squash_merge, .allow_merge_commit, .allow_rebase_merge'
# Dependabot PRs: use --rebase (others blocked by policy)
gh pr merge <pr-number> --rebase

# Conflicting Dependabot PR → apply directly to main
# 1. Check what the bump changes
gh pr diff <pr-number>
# 2. Apply the change to main files
# 3. Commit and close the PR
git add requirements-dev.txt pyproject.toml  # or relevant lockfiles
git commit -m "chore(deps-dev): bump <package> from X to Y"
gh pr close <pr-number> --comment "Applied directly to main (conflict after other bumps landed). Closes #<pr-number>."

# Stale audit issue: check current state before acting
gh issue view <number> --comments
git log --oneline main | head -20   # confirm items already on main

# Close aggregate issue after sub-issues resolved
gh issue close <number> --comment "All sub-issues resolved: #N1, #N2, #N3 (PRs merged). Closing."
```

### Determine Repo Merge Policy

Before touching any PRs, check what merge methods are allowed:

```bash
gh api repos/<owner>/<repo> --jq '{
  squash: .allow_squash_merge,
  merge_commit: .allow_merge_commit,
  rebase: .allow_rebase_merge
}'
```

In repos that enforce **rebase-only**:
- `gh pr merge --squash` → "Repository does not allow squash merging"
- `gh pr merge --merge` → "Repository does not allow merge commits"
- `gh pr merge --rebase` → works

Always use `gh pr merge --rebase` in rebase-only repos. For Dependabot PRs specifically, `--rebase` is always the correct flag.

### Merge Sequential Dependabot PRs

List and sort Dependabot PRs by number (oldest first = least likely to conflict):

```bash
gh pr list --state open --author dependabot --json number,title,headRefName,mergeStateStatus \
  | python3 -c "
import json, sys
prs = json.load(sys.stdin)
for p in sorted(prs, key=lambda x: x['number']):
    print(f\"#{p['number']:5d} [{p['mergeStateStatus']:12s}] {p['title']}\")
"
```

Merge each in order, oldest first:

```bash
gh pr merge <pr-number> --rebase
```

After each merge, wait for the next PR's CI to update before merging it.

### Handle a Conflicting Dependabot PR

When a Dependabot PR goes CONFLICTING after other bumps land:

**Option A: Wait for Dependabot rebase** (preferred if not urgent)
- Post a comment `@dependabot rebase` on the PR
- Wait 5–15 minutes for Dependabot to push a rebased commit

**Option B: Apply directly to main** (use when Dependabot rebase is slow or already tried)

```bash
# 1. See exactly what the PR changes
gh pr diff <pr-number>

# 2. Apply the change(s) to main directly
# For a requirements-dev.txt bump:
sed -i 's/package==OLD/package==NEW/' requirements-dev.txt

# 3. Verify the change
git diff

# 4. Commit to main
git add requirements-dev.txt pyproject.toml
git commit -m "$(cat <<'EOF'
chore(deps-dev): bump <package> from X to Y

Applying Dependabot PR #<number> directly to main after conflict.
The bump was blocked by conflicts from other Dependabot bumps landing first.
EOF
)"

# 5. Close the stale PR
gh pr close <pr-number> --comment "Applied directly to main (conflict from sequential Dependabot bumps). Resolved."
```

**Why this works**: The conflict is purely positional (version string changed in the same line in both the branch and main). The semantic intent (bump the version) is already achieved by direct application.

### Triage a Stale Issue Audit

When an issue audit was filed weeks/months ago, check current state before acting:

```bash
# Read the issue (requirements listed)
gh issue view <number>

# Check what's been done since the audit
git log --oneline --since="<audit-date>" main | head -30

# For each item in the audit, verify on main:
ls <expected-files>
git show main:<path/to/file> | head -5

# If items already exist:
gh issue close <number> --comment "Resolved: <item1> exists at <path>, <item2> merged in PR #N. All audit items addressed."
```

**Key rule**: Never start implementing audit items without first checking whether they've already been done. Audits become stale rapidly on active repos.

### Fix ruff E402 in Test Files (conftest.py sys.path pattern)

When a test file fails CI with `E402 Module level import not at top of file`:

**Root cause**: The test file manually adds to `sys.path` (e.g., `sys.path.insert(0, ...)`) before imports. ruff sees the imports below the `sys.path` manipulation as E402 violations.

**Fix**: Remove the `sys.path` manipulation from individual test files. Use `conftest.py` for this.

```python
# BAD — in test_foo.py (causes E402 on all imports below):
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
import my_module   # E402: module level import not at top of file

# GOOD — conftest.py handles sys.path; test_foo.py has clean imports:
import pytest
import my_module   # no E402 — conftest ran first
```

Check if conftest.py already handles the path:

```bash
# Check repo conftest files
find <project-root> -name "conftest.py" | xargs grep -l "sys.path" 2>/dev/null
```

### Fix ruff Unused Import Warnings in Test Files

When CI shows `F401 'patch' imported but unused` or `F401 'pytest' imported but unused`:

```bash
# Check which imports are actually used
grep -n "patch\|@pytest.mark\|pytest\." test_file.py

# Remove unused imports
# If 'patch' is imported but mock.patch is used inline:
# from unittest.mock import patch  → remove if using mock.patch() directly
```

**Pattern**: Test files generated by sub-agents often import `patch` from `unittest.mock` but use `mock.patch()` as a context manager directly — the standalone `patch` import is unused.

### Close Aggregate Audit Issues

When an issue is an aggregate tracker ("All X issues should be fixed"):

```bash
# Verify all sub-issues are closed
gh issue list --label <label> --state open  # should be empty

# Close with summary
gh issue close <number> --comment "$(cat <<'EOF'
All items in this audit have been resolved:
- #N1: resolved via PR #M1
- #N2: resolved via PR #M2
- #N3: already existed on main (confirmed <date>)

Closing this aggregate tracker.
EOF
)"
```

---

## CodeQL Missing Workflow Permissions Fix

### Steps to Fix CodeQL `actions/missing-workflow-permissions` Alert

1. **Fetch the alert details** to get the exact file and line numbers:
   ```bash
   gh api repos/<OWNER>/<REPO>/code-scanning/alerts/<ALERT_NUMBER>
   ```
   Look for `location.path` and `location.start_line` in the response.

2. **Read the flagged workflow** to understand what it does:
   - Does it only check out code and run scripts? → `permissions: contents: read`
   - Does it push artifacts, create releases, or write to packages? → add those scopes too

3. **Cross-check sibling workflows** for reference:
   ```bash
   grep -A5 "permissions:" .github/workflows/*.yml
   ```
   Sibling workflows with similar jobs reveal the expected permission pattern.

4. **Add the permissions block** between `on:` and `jobs:`:
   ```yaml
   on:
     push:
       branches: [main]
     pull_request:
       branches: [main]

   permissions:        # <-- Add here
     contents: read

   jobs:
     validate:
       ...
   ```

5. **Validate the YAML syntax** locally before committing:
   ```bash
   python3 -c "import yaml; yaml.safe_load(open('.github/workflows/<filename>.yml'))" && echo "YAML OK"
   ```

6. **Submit via PR**: Create a branch, commit, push, and open a PR against main.

**Before fix** (flagged by CodeQL `actions/missing-workflow-permissions`):
```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  validate:
    runs-on: ubuntu-latest
    ...
```

**After fix**:
```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  contents: read

jobs:
  validate:
    runs-on: ubuntu-latest
    ...
```

**Locating the CodeQL alert**:
```bash
# List all code scanning alerts for a repo
gh api repos/<OWNER>/<REPO>/code-scanning/alerts

# Fetch a specific alert (includes file path and line numbers)
gh api repos/<OWNER>/<REPO>/code-scanning/alerts/<N>
```

---

## Karma/Playwright Chromium Setup for CI

### Steps to Configure Playwright-Managed Chromium for Karma

1. Install `playwright` in the CI job and download Chromium with `npx playwright install --with-deps chromium`.
2. Resolve the Playwright Chromium executable path from Node instead of probing system Chrome locations.
3. Wrap that executable in a small shell script that adds `--no-sandbox` and `--disable-dev-shm-usage`.
4. Export the wrapper path through `CHROME_BIN` so Karma's Chrome launcher API uses the Playwright binary.
5. Rename the Karma custom launcher to something explicit like `PlaywrightChromiumHeadless` so the workflow contract reflects the real browser source.
6. Keep in mind that Karma logs may still say `Starting browser ChromeHeadless` because the underlying launcher implementation comes from `karma-chrome-launcher`.

```bash
# CI step
npm install --no-save playwright
npx playwright install --with-deps chromium

chrome_bin=$(node -e "console.log(require('playwright').chromium.executablePath())")
cat > "$RUNNER_TEMP/chrome-headless-radiance" <<'EOF'
#!/usr/bin/env bash
exec "$chrome_bin" --no-sandbox --disable-dev-shm-usage "$@"
EOF
chmod +x "$RUNNER_TEMP/chrome-headless-radiance"
echo "CHROME_BIN=$RUNNER_TEMP/chrome-headless-radiance" >> "$GITHUB_ENV"

npm test -- --watch=false --browsers=PlaywrightChromiumHeadless
```

Useful validation commands:

```bash
npm test -- --watch=false --browsers=PlaywrightChromiumHeadless \
  --include src/services/radiance_run_service.spec.ts \
  --include src/components/radiance_source_input/radiance_source_input.spec.ts \
  --include src/components/visualizer/worker/graph_processor.spec.ts \
  --include src/components/visualizer/worker/graph_layout.spec.ts

pytest -q tests/backend/test_ci_contract.py
```

Expected local signal:

```text
TOTAL: 10 SUCCESS
pytest: 6 passed
```

---

## Packaged Frontend Functional Asset Validation

### Steps to Replace Brittle Drift Checks with Functional Validation

1. Rebuild the packaged frontend exactly the way the repository ships it, not just the development bundle.
2. Serve the packaged `web_app` directory over a local loopback HTTP server inside the validator.
3. Fetch `index.html` and parse local `script`, `stylesheet`, `icon`, and preload URLs dynamically instead of hardcoding hashed filenames.
4. Fetch each discovered local asset and fail if any request is non-`200` or returns an empty body.
5. Parse CSS asset bodies for `url(...)` references and verify those local assets as well.
6. Run the validator from CI immediately after `npm run deploy` so the workflow proves the shipped package is internally consistent.

```bash
# 1. Rebuild packaged assets from the UI source tree
cd vendor/model_explorer/src/ui
npm ci
npm run deploy

# 2. Validate the packaged frontend runtime surface
cd /path/to/repo
python3 scripts/checks/validate_packaged_frontend.py
```

Recommended validator behavior:

```text
Input root: vendor/model_explorer/src/server/package/src/model_explorer/web_app
Server bind: 127.0.0.1 on ephemeral port
Accepted URLs: only http://127.0.0.1:<ephemeral>/...
Validation surface:
- index.html
- local script assets
- local stylesheet assets
- local icon/preload assets
- local CSS url(...) assets
Failure conditions:
- non-200 response
- empty response body
- no local assets discovered in index.html
```

Observed useful command sequence:

```bash
npm run deploy
python3 scripts/checks/validate_packaged_frontend.py
bandit -q -r radiance scripts --severity-level medium --confidence-level medium
```

---

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Read only last few lines | Used `tail` to check end of log | Missed earlier context and root cause | Read full log or use grep for patterns |
| Search for single keyword | Grepped only "error" | Missed "FAILED", "panic", "exception" variants | Use multiple error patterns together |
| Analyze without PR context | Looked at logs in isolation | Couldn't connect to code changes | Always compare with PR diff |
| Skip stack traces | Focused only on error message | Missed actual source location | Full stack trace shows root cause |
| Check if failure is pre-existing using only PR CI output | Looked at PR CI output without comparing to main history | Cannot tell if failure pre-exists without checking main branch runs | Always cross-reference against `gh run list --branch main` |
| Assume all CI failures are PR-caused | Treated `Core ExTensor` crash as caused by serialization change | ExTensor crashes are flaky runtime crashes unrelated to the serialization fix | Check which files the failing test covers vs which files you changed |
| Wait for log output before run completes | Called `gh run view --log-failed` while run still in progress | GitHub returns "run is still in progress; logs will be available when it is complete" | Check `gh run view` status first; use `gh run watch` for background waiting |
| Controlled experiment without `--Werror` | Ran heavy vs light import tests 30x locally | 0 crashes — the JIT crash hypothesis was untestable without `--Werror` | Always reproduce with exact CI flags first |
| Controlled experiment in Docker (GLIBC 2.35) | Ran same tests 30-100x in Docker matching CI env | Still 0 crashes — the crash wasn't GLIBC-dependent | Environment matching alone doesn't reproduce if the failure mode is wrong |
| Heap corruption reproduction (25 tests in one file) | Ran monolithic test file 50x locally and in Docker | 0 crashes — heap corruption also not reproducible | Historical bugs may already be fixed; verify before building workarounds |
| Searching CI logs for "execution crashed" | Searched 10+ recent CI runs | Zero instances found — the actual errors were compile failures | Read the logs before assuming the failure mode |
| Docker bind-mount pixi install | Ran `pixi install` inside Docker with shared `.pixi/` | Corrupted host Mojo installation (hardcoded paths) | Never share `.pixi/` between host and Docker; use separate volumes |
| Assuming failures require fixes | Saw red CI and started planning fixes | Both failures were pre-existing on main | Always check main's CI history before concluding a PR introduced failures |
| Root-relative link analysis | Worried new links in CLAUDE.md would trigger lychee errors | New links used relative paths, not root-relative; all targets existed | Distinguish root-relative (`/path`) from relative (`path`) — lychee fails on root-relative, not relative |
| Blaming doc PR for test crashes | `execution crashed` failures looked alarming | These were infrastructure-level crashes on main unrelated to docs | `execution crashed` (runtime) vs test assertion failures are different root causes |
| Fixing Mojo runtime crashes in PR | Attempted to diagnose `mojo: error: execution crashed` in test files | The PR changed zero `.mojo` files — Mojo crashes cannot be caused by markdown changes | Always check `git diff main...HEAD --name-only` before attempting any CI fix |
| Treating link-check as PR-caused | Assumed `link-check` failure was introduced by new markdown files | The failing links were in `docs/adr/README.md` and `notebooks/README.md`, neither touched by PR | Cross-reference failing file paths against PR diff before investigating |
| Running tests to verify Mojo failures | Considered running `pytest tests/` to confirm | The test failures are Mojo runtime crashes, not Python tests; running locally without CI environment won't help | Match the test runner to the failing workflow type |
| Immediately fixing CI | Jumping to fix CI failures without first verifying their origin | Would have introduced unnecessary changes to a PR that was already correct | Always verify failure origin before implementing fixes |
| Skipping verification | Trusting the review plan without independent confirmation | Could miss genuine issues introduced by the PR | Run the grep/ls checks even if the plan says no fixes needed |
| Assuming CI failures require a fix on cleanup PR | Automatically trying to fix red CI checks | The failures were unrelated to the PR — pre-existing on main from infrastructure issues | Always verify CI failure history on `main` before attempting any fix |
| Committing review instructions file | Including `.claude-review-fix-*.md` in the commit | These are temporary instruction files, not implementation files | Never commit review instruction/orchestration files |
| Assumed all failures were transient | Initially classified all 3 failing PRs as transient without checking logs | PR had a real pip dependency conflict (pytest-benchmark needs pytest>=8.1 but we downgraded to 7.4.4) | Always check the actual error logs, not just the failure count. Config PRs can cause real failures in dependency resolution. |
| Tried re-running still-running jobs | Used `gh run rerun` on a run that was still in progress | Got "cannot be rerun; This workflow is already running" | Check run conclusion before attempting re-run: only re-run when conclusion is "failure", not when empty (in-progress). |
| Bulk re-run without checking status | Tried re-running all failed runs at once | Some runs had already been re-run or were still in progress | Always check individual run status with `gh run view <ID> --json conclusion` before re-running. |
| Analyzing crash stack traces directly | Tried to identify crash cause from `libKGENCompilerRTShared.so` frame addresses | Stack frames are in stripped libraries with no symbols — no useful info | Runtime crashes in Mojo stdlib libs are not debuggable without symbolicated builds |
| Checking if `__str__` conformance causes issues | Hypothesized adding `__str__` changes Mojo trait resolution and causes downstream crashes | Could not confirm — tests that don't call `__str__` still crashed | Cannot infer crash cause from Mojo trait changes without being able to run the code locally |
| Comparing crash timestamps to identify common cause | Looked for timing correlation between crashes | Multiple crashes happened in parallel jobs — no useful pattern | Parallel CI jobs don't share state; crashes in unrelated jobs indicate infrastructure flakiness |
| Waiting for CI to complete before re-running | First attempt was to fully analyze before re-running | Wasted time on inconclusive analysis | Re-run should be triggered early as the fastest flakiness signal |
| Adding lint as a step in the test job | Considered adding ruff as a step inside existing test matrix | Would run redundantly for each matrix entry; couples lint to test failures | Use a separate job — runs once, in parallel, with independent failure reporting |
| Protecting branch "main" when default was "master" | Earlier enforcement script assumed all repos use `main` | GitHub API returned 404 "Branch not found" for repos with `master` default | Always detect actual default branch via API; never assume "main" |
| `gh api --jq` with `parse_json=True` | Used `parse_json=True` when `--jq` extracts a scalar | `json.loads("master")` fails; wrong branch for 5 repos | When `--jq` extracts a scalar, use `parse_json=False` — output is plain text, not JSON |
| Including Dependabot/CodeQL jobs as required checks | Initial audit recommended `Analyze (actions)`, `Dependabot` | These are GitHub-automated jobs that don't run on every PR | Filter out automated job names; requiring them would block all PRs |
| `min-runs=1` for all repos | Lowered threshold to include repos with limited CI history | Included 19+ jobs with only 1 run (benchmarks, container builds) — too aggressive | Keep `min-runs=3`; jobs that only ran once are likely scheduled/manual, not PR-triggered |
| Including path-filtered workflows as required checks | Shell Tests (`bats`) passes 100% but triggers only on `**/*.sh` | PRs not touching `.sh` files would never get the check and be blocked forever | Detect `paths:` filter in workflow YAML; exclude those jobs from required checks |
| Assumed all CI failures were JIT flakes | Investigated `libKGENCompilerRTShared.so` crashes as the sole root cause | Only 1 of 4 failing tests was actually a JIT crash; rest were parse errors and a logic bug | Always read actual CI error output — classify each failure individually |
| Assumed debug_assert was broken in JIT | Created self-contained reproducer with 2 call sites | Reproducer PASSED — debug_assert works fine in isolation | The issue isn't debug_assert itself; it's cumulative inlining overhead at 100+ call sites |
| Relied on Podman storage cache | Cached `~/.local/share/containers` keyed on Dockerfile hash | Podman storage directory exceeded 10 GB cache limit — tar save always failed silently | Image tar cache (`podman save/load`) is much smaller and stays under the limit |
| Retry logic to handle JIT crashes | `run_test_group.sh` had 3-attempt retry with exponential backoff | Retry masked real deterministic failures | Retry is a workaround, not a fix; remove it to make all failures immediately visible |
| Include shared/ in `_build-inner` find for mojo build | Added shared/ .mojo files to the `mojo build` loop | `mojo build` requires `fn main()` — library modules don't have one | Library code must be validated with `mojo package`, not `mojo build` |
| `type: ignore[no-redef]` on tomllib import | Added type:ignore to suppress mypy on tomli fallback | CI runs Python 3.12 where tomllib exists, so mypy flags the ignore as unused | Use `importlib.import_module()` — zero type annotations needed |
| RUF059 rename then forget references | Renamed `versions` to `_versions` but left `assert versions == {}` on next line | F821 undefined name | After any RUF059 rename, grep for remaining references to the old name |
| Format after lint fix | Fixed lint issues then expected format to be clean | Lint fixes can change formatting | Always run format AFTER lint fixes |
| Leave original test file after adding glob-covered parts | Kept `test_elementwise.mojo` alongside split parts | `validate_test_coverage.py` reports original as "uncovered" | Original must be deleted; split files fully replace it |
| Inline `${{ github.event_name }}` in `run:` | Used expression directly in shell | Pre-commit security hook blocked the edit (workflow injection risk) | Always use `env:` block even for non-sensitive context values |
| Glob tool for .github/workflows files | Used Glob with `.github/workflows/*.yml` | Glob doesn't match hidden directories | Use Bash or full paths instead |
| `workflow_dispatch` to trigger CI on Keystone | Triggered CI via `gh workflow run` to get fresh failure logs | Job cancelled during provisioning | Workflow dispatch may be cancelled by concurrency settings; use push-triggered runs |
| `gh pr merge --squash` on Dependabot PR | Used squash merge for a dependency bump | "Repository does not allow squash merging" | Check repo merge policy first; only `--rebase` works in rebase-only repos |
| `gh pr merge --merge` on Dependabot PR | Used merge commit flag | "Repository does not allow merge commits" | Same lesson — always use `--rebase` in rebase-only repos |
| Waiting for `@dependabot rebase` to land | Posted rebase comment on PR #1238; waited several minutes | Comment triggers async rebase; no guarantee it completes in time | If rebase comment doesn't land within ~10 min, apply directly to main and close the PR |
| Implementing all items from an audit issue | Started implementing items from Issue #924 without checking current state | SECURITY.md, CONTRIBUTING.md, CODE_OF_CONDUCT.md, pytest CI, and validate scripts all already existed on main | Always check current state of repo before acting on audit items; audits go stale quickly |
| Duplicate `sys.path` block in test files | Sub-agent added `sys.path.insert()` in every test file because conftest.py pattern wasn't checked | Caused ruff E402 on all imports below the `sys.path` block | Check for conftest.py `sys.path` handling before generating test files; never duplicate in test files |
| Keeping unused `patch` import from `unittest.mock` | Generated tests imported `patch` for anticipated use | `patch` was never used directly (used `mock.patch()` context manager instead) | After generating test files, run `ruff check --select F401` to catch unused imports before pushing |
| N/A (CodeQL permissions fix) | Direct approach worked on first try | N/A | The CodeQL permissions fix is always a 2-line YAML block; no complex debugging needed |
| System Chrome discovery | Looked up `google-chrome`, `chromium`, or `chromium-browser` on the runner | Depends on runner image state and reintroduced exactly the environment variability the fix was trying to remove | Install and own the browser dependency inside the job |
| Keeping the old Karma launcher contract | Left the workflow and CI contract tests pinned to `ChromeHeadless` strings | The repo's own CI contract tests then failed even though the browser source changed correctly | Update test contracts and workflow text together when renaming CI launchers |
| Treating "Playwright" as a full Karma launcher replacement | Expected the runtime logs to stop mentioning `ChromeHeadless` entirely | Karma still uses the Chrome launcher plugin under the hood, so only the binary source changed | Distinguish between launcher API name and actual browser binary source |
| Hardcoded drift gate for packaged frontend | Used `git diff --exit-code` after `npm run deploy` | Rebuilds legitimately changed hashed bundle names like `main-*.js`, making CI fail even when the packaged app still worked | Generated filename drift is not a functional failure; validate runtime reachability instead |
| Narrow `index.html` diff inspection | Looked only at `index.html` script-tag rewrites | That explains why CI failed, but does not prove the packaged frontend is healthy or complete | Turn diagnosis into an executable validator that checks all discovered local assets |
| Generic `urllib.request.urlopen` in validator | Used `urlopen()` for convenience in the functional validator | Bandit flagged it as `B310` because it accepts broader URL schemes than necessary | Keep the validator on an explicit trust boundary and fetch only loopback `http://127.0.0.1:<port>` assets |

## Results & Parameters

### Output Format for CI Analysis Report

Provide analysis with:

1. **Error Category** — Type of failure (compilation, test, timeout, dependency, environmental, JIT crash)
2. **Root Cause** — What line/code caused the failure
3. **Context** — Full error message and stack trace
4. **Related Changes** — Which PR changes might have caused it
5. **Remediation** — Recommended fix or investigation steps

### Classification Decision Tree

```
CI check fails on your PR
├── Does the error reference a file you changed?
│   ├── YES → PR-caused, fix it
│   └── NO → Continue...
│
├── Does the same job fail on recent main branch runs?
│   ├── YES → Pre-existing, not your fault, ignore
│   └── NO → Continue...
│
├── Does the failing test group cover files you changed?
│   ├── NO → Strong flakiness signal — re-run CI
│   └── YES → Continue...
│
└── Does the same job PASS on other open PRs / last successful main?
    ├── YES → Flaky, re-run with --failed
    └── NO → Possibly a shared regression, investigate further
```

**Re-run verdict interpretation:**
- Re-run passes → Flaky CI, no fix needed
- Re-run fails → Infrastructure problem, check with team

### Dependabot PR Resolution Decision Tree

```
Dependabot PR open?
├── MERGEABLE → gh pr merge <N> --rebase
├── CONFLICTING →
│   ├── Post @dependabot rebase comment → wait 10 min
│   │   ├── PR rebased → gh pr merge <N> --rebase
│   │   └── Still conflicting → apply directly to main (Phase 3)
│   └── Apply directly to main + close PR
└── BLOCKED (CI failing) →
    ├── Check required checks: gh api repos/owner/repo/branches/main --jq '.protection.required_status_checks.contexts[]'
    └── Fix the actual failure before merging
```

### Failure Classification Matrix (Batch PRs)

```yaml
failure_types:
  real_failure:
    example: "pip ResolutionImpossible - pytest-benchmark 5.2.3 requires pytest>=8.1"
    diagnosis: "Check error message, verify files changed could cause this"
    fix: "Launch dedicated agent to fix the specific issue"

  flaky_mojo_jit:
    example: "mojo: error: execution crashed (Core Utilities, Tensor, Shared Infra)"
    diagnosis: "Same tests pass on other PRs with identical main branch"
    fix: "gh run rerun <RUN_ID> --failed"

  transient_infrastructure:
    example: "HTTP 429 Too Many Requests (CodeQL), HTTP 500 (pixi CDN)"
    diagnosis: "External service error, not related to code"
    fix: "gh run rerun <RUN_ID> --failed"

  test_report_cascade:
    example: "Test Report job fails because upstream test job failed"
    diagnosis: "Dependent job, will pass when upstream re-run succeeds"
    fix: "Fix/re-run the upstream job, report job auto-resolves"
```

### Key Insight: Config PRs and Mojo Test Failures

```yaml
# PRs that ONLY change these files should NEVER cause Mojo test failures:
safe_file_types:
  - "*.md"           # Documentation
  - ".gitignore"     # Git config
  - "justfile"       # Build recipes
  - "*.yml"          # CI workflows (unless changing test commands)
  - "*.yaml"         # Config files

# If these PRs show Mojo failures, they are ALWAYS flaky JIT crashes
# Exception: requirements.txt/pixi.toml can cause pip install failures
```

### Mojo --Werror Fix Reference

```diff
# Mojo 0.26.1: alias deprecated, replace with comptime
- alias MY_CONST: Int = 42
+ comptime MY_CONST: Int = 42
```

### Environment Comparison for Misdiagnosis

| Parameter | Local | Docker | CI |
| ----------- | ------- | -------- | ----- |
| GLIBC | 2.39 | 2.35 | 2.35 |
| Mojo | 0.26.1 | 0.26.1 | 0.26.1 |
| `--Werror` | No (default) | No (default) | Yes |
| Crash rate | 0% | 0% | 100% (compile error) |

### Success Criteria for "Safe to Merge"

- [ ] `git diff main...HEAD --name-only` shows only documentation/config files
- [ ] Failing test groups match failures visible on recent `main` CI runs
- [ ] `pre-commit` CI check passes (the check that validates changed files)
- [ ] `test-agents` CI check passes (if agent configs were modified)

### Error Handling

| Problem | Solution |
| --------- | ---------- |
| Logs not accessible | Use `gh run view` to check permissions |
| Truncated logs | Download full artifact instead of view |
| Large log files | Use grep to extract relevant sections |
| Encoded artifacts | Unzip and decompress before analysis |

### Common Pre-Existing Failures (ProjectOdyssey)

| Check | Status | Notes |
| ------- | -------- | ------- |
| `link-check` | Pre-existing | Root-relative links (`/.claude/...`) fail on all PRs — lychee needs `--root-dir` |
| `Core ExTensor` | Intermittent flaky | Mojo runtime crash; passes on other PRs; re-run resolves it |
| `Core Initializers` | Intermittent flaky | Same pattern as Core ExTensor |
| `Core Activations` | Pre-existing infrastructure | `mojo: error: execution crashed` pre-dates most PRs |
| `Check Markdown Links` | Pre-existing | lychee cannot resolve root-relative paths (`/.claude/shared/`) — 5+ consecutive failures on main |

### Key Commands Reference

```bash
# Verify no stale references remain
grep -rn "old-filename.md" . --include="*.md"

# Confirm deleted file is gone
ls agents/old-filename.md

# Confirm CI failure is pre-existing
gh run list --branch main --limit 5 --json name,conclusion

# Confirm Mojo crash pre-existing on main
gh run view <MAIN_RUN_ID> --json jobs | python3 -c \
  "import json,sys; [print(j['name'],j['conclusion']) for j in json.load(sys.stdin)['jobs'] if 'Activ' in j['name']]"

# Verify CI run ID cited in a review plan
gh run view <run-id> --json jobs | python3 -c \
  "import json,sys; [print(j['name'],j['conclusion']) for j in json.load(sys.stdin)['jobs'] if 'FailingJob' in j['name']]"

# Check pre-commit locally
pixi run pre-commit run --all-files 2>&1 | tail -20

# Check failed check names for a PR
gh pr checks <PR> | grep fail | awk '{print $1}'
```

### Ruff Lint Job Parameters

| Decision | Rationale |
|----------|-----------|
| Separate job (not step) | Parallel execution, clearer failure attribution |
| 10-minute timeout | Lint is fast; 30 minutes is wasteful |
| No `setup-python` in lint job | Pixi manages Python; redundant with `setup-pixi` |
| Simpler cache key | No matrix dimensions to vary |

### Org-Wide CI Governance Parameters

| Parameter | Default | Notes |
|-----------|---------|-------|
| `--runs` | 10 | Number of recent runs to analyze per repo |
| `--min-runs` | 3 | Minimum executed runs for a job to qualify |
| `--min-pass-rate` | 1.0 | Required pass rate (1.0 = 100%) |
| `--include-path-filtered` | false | Include path-filtered jobs (risky) |

### Flaky CI Classification Statistics

| Metric | From ProjectOdyssey PR #5097 |
|--------|------------------------------|
| Total CI failures investigated | 4 unique test files |
| Infrastructure failures | 1 (Docker 504) |
| Deterministic code bugs | 3 (parse errors + logic bug) |
| Genuine JIT flakes | 1 |
| "Flaky" that were actually deterministic | 75% |

### Mojo JIT Threshold Model

The Mojo JIT compiler has an internal buffer that overflows after enough code is compiled. `debug_assert` in 3 `@always_inline` methods × 100+ call sites = significant overhead. Whether a specific test crashes depends on: (1) how much the test imports, (2) how many `@always_inline` methods are instantiated, (3) JIT cache state (fresh in CI, warm locally), (4) memory layout.

### Pre-commit Fix Iteration Pattern (Cross-Python-Version)

```
Iteration 1: Fix format + unused imports + mypy type:ignore + C901 + coverage
Iteration 2: Fix remaining RUF059 + F821 from variable renames
Iteration 3: Fix importlib approach for tomllib + D301 + SIM102 + E501
```

### Rollback for Required Checks

```bash
# Manual rollback for a single repo
gh api --method PATCH repos/ORG/REPO/branches/BRANCH/protection/required_status_checks \
  --input - <<< '{"strict":false,"contexts":["original","checks","only"]}'

# Remove branch protection entirely
gh api --method DELETE repos/ORG/REPO/branches/BRANCH/protection
```

### Repo Merge Policy Detection

```bash
# Quick check — if any are false, that method is blocked
gh api repos/<owner>/<repo> --jq '.allow_squash_merge, .allow_merge_commit, .allow_rebase_merge'
# false / false / true → rebase-only repo
```

### Issue Audit Checklist

Before acting on any audit/batch issue:

1. `gh issue view <number>` — read all requirements
2. For each requirement: `ls <path>` or `git show main:<path>` — does it exist?
3. For any CI requirement: `gh run list --branch main --limit 5` — is it running?
4. If >80% already done: close the issue with evidence, don't re-implement

### ruff Lint Quick Fix Reference

| Error | Cause | Fix |
|-------|-------|-----|
| `E402 Module level import not at top` | `sys.path` manipulation before imports | Remove duplicate `sys.path` block; conftest.py handles it |
| `F401 imported but unused` | Generated test imports `patch` but never calls it standalone | Remove unused import |
| `E501 Line too long` | Long test assertion strings | Break string across lines with `(` `)` |
| `E303 too many blank lines` | Extra blank lines in test file | Remove extra blank lines |

### Permission Level Guide

| Workflow Type | Recommended Permissions |
|---------------|------------------------|
| Validate / lint / check (read-only) | `contents: read` |
| Test matrix (read-only) | `contents: read` |
| Release / publish to package registry | `contents: write`, `packages: write` |
| Auto-merge / update PR | `contents: write`, `pull-requests: write` |
| Security scan with SARIF upload | `contents: read`, `security-events: write` |

### Karma/Playwright Chromium Setup Parameters

```text
Browser provider: Playwright-installed Chromium
Karma launcher name: PlaywrightChromiumHeadless
Env var bridge: CHROME_BIN
Required flags:
- --no-sandbox
- --disable-dev-shm-usage
```

### Packaged Frontend Validator Parameters

```text
Input root: vendor/model_explorer/src/server/package/src/model_explorer/web_app
Server bind: 127.0.0.1 on ephemeral port
Accepted URLs: only http://127.0.0.1:<ephemeral>/...
Validation surface:
- index.html
- local script assets
- local stylesheet assets
- local icon/preload assets
- local CSS url(...) assets
Failure conditions:
- non-200 response
- empty response body
- no local assets discovered in index.html
```

### Scale Reference (Dependabot PRs)

| Task | Method | Time |
|------|--------|------|
| 5 sequential Dependabot PRs (no conflicts) | `gh pr merge --rebase` per PR | ~2 min total |
| 1 conflicting Dependabot PR | Apply directly to main + close | ~5 min |
| Stale issue audit (3 issues) | Check current state, close with evidence | ~10 min |
| Sub-agent test PR with ruff lint failures | Fix on branch directly, push | ~15 min |
| Myrmidon sub-agent for text-change task | Delegate via swarm | ~90 sec wall-clock, 7 tool calls |

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | PR #336 CI diagnosis | Multiple CI check triage and fix |
| ProjectOdyssey | PR #4494 / #4898 Mojo JIT vs compile error misdiagnosis | alias→comptime fix |
| ProjectOdyssey | PR #4897 Dockerfile + pre-commit triage | GID collision + bash -c args |
| ProjectOdyssey | PR #3363 / issue #3158 — CLAUDE.md trim | Both failures confirmed pre-existing; PR merged without fixes |
| ProjectOdyssey | PR #3334 / issue #3147 — cleanup PR | Zero fixes needed; `Core Activations` and `link-check` pre-existing |
| ProjectOdyssey | PR #3338 / issue #3150 — ADR index update | Docs-only; `Core Elementwise`, `Core Tensors` pre-existing |
| ProjectOdyssey | Multiple docs/agent config PRs | Mojo runtime crashes on docs-only PRs consistently pre-existing |
| ProjectOdyssey | Diagnosed CI across 14 batch PRs after wave-based triage | 1 real fix (pip conflict), 6 flaky re-runs, 7 clean passes |
| ProjectOdyssey | PR #2722 ExTensor utility methods | Core Tensors/Initializers flaky crash confirmed; re-run resolved |
| ProjectOdyssey | PR #5097 flaky CI triage | Infrastructure 504, deterministic parse errors, and genuine JIT flake classified separately |
| ProjectOdyssey | Org-wide required checks enforcement | Enforced `min-runs=3`, excluded path-filtered and automated jobs |
| ProjectOdyssey | Branch rename master→main (org-wide) | CI fixed across multiple repos; self-hosted runner issues resolved |
| ProjectMnemosyne | 6 Dependabot PRs (pytest, PyYAML, certifi, etc.), Issues #909/#916/#924, 2026-04-14 | PRs #1278/#1279 merged with CI passing; PR #1238 (pytest 9.0.3) applied to main directly |
| ProjectMnemosyne | CodeQL alert #2 on `validate-plugins.yml` | Added `permissions: contents: read` between `on:` and `jobs:` blocks |
| Radiance | PR #110 rebase + frontend CI browser change | Rebased against `origin/master`, resolved workflow conflict in favor of Playwright Chromium, and updated the CI contract to match |
| Radiance | PR #110 CI remediation | Replaced the packaged frontend `git diff` gate with a runtime asset validator and confirmed it locally before pushing |
