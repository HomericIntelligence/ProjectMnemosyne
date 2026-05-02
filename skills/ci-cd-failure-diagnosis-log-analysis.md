---
name: ci-cd-failure-diagnosis-log-analysis
description: "Diagnose CI failures by reading logs, identifying error patterns, and classifying root causes. Use when: (1) CI pipeline fails and you need to understand why, (2) tests pass locally but fail in CI, (3) multiple unrelated checks fail simultaneously, (4) CI retry logic labels failures as JIT crashes, (5) need to distinguish Mojo JIT crashes from real compile/test errors, (6) CI fails on a PR but PR changes look unrelated to failures, (7) docs-only or cleanup PRs show red CI, (8) multiple batch PRs all show BLOCKED status, (9) need to decide whether to block merge or proceed."
category: ci-cd
date: 2026-03-28
version: "2.0.0"
user-invocable: false
verification: unverified
tags:
  - ci-failure
  - flaky-tests
  - mojo-jit
  - batch-pr
  - diagnosis
  - pre-existing
---

# CI Failure Diagnosis and Log Analysis

## Overview

| Date | Objective | Outcome |
| ------ | ----------- | --------- |
| 2026-03-28 | Consolidated diagnosis and log-analysis knowledge for CI failures | Operational |
| 2026-04-12 | v2.0.0: Absorbed pre-existing failure triage, batch PR diagnosis, and crash decision tree | Merged |

Systematic approach to reading CI logs, identifying error patterns, classifying failure types
(PR-caused vs pre-existing vs flaky), and diagnosing root causes before attempting fixes.
Covers single-PR diagnosis, batch PR diagnosis across many PRs, and the decision tree for
distinguishing infrastructure crashes from real regressions.

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
