---
name: flaky-ci-crash-diagnosis
description: 'Diagnose whether CI test crashes are caused by code changes or pre-existing
  flakiness. Use when: widespread ''execution crashed'' failures appear on a PR but
  affect tests unrelated to the changes.'
category: debugging
date: 2026-03-05
version: 1.0.0
user-invocable: false
---
## Overview

| Attribute | Value |
|-----------|-------|
| Category | debugging |
| Complexity | Medium |
| Time to Apply | 10-20 minutes |
| Risk | Low (read-only analysis) |
| Mojo Version | 0.26.1+ |

Diagnose CI test crashes on a PR to determine if they are regressions introduced by the
changes or pre-existing flakiness. Guides systematic comparison between PR CI results and
historical main branch results to reach a confident verdict.

## When to Use

1. A PR has CI jobs showing `error: execution crashed` failures
2. The crashing tests are in files that do NOT use any of the newly added/changed code
3. You need to decide whether to investigate a fix or simply re-run CI
4. Multiple unrelated test groups crash simultaneously on the PR

## Verified Workflow

### Step 1: Identify failing CI jobs

```bash
# Get the run ID for the PR's CI
gh run list --workflow "Comprehensive Tests" --branch <branch> --limit 3 --json status,conclusion,databaseId

# List all failed jobs
gh run view <run-id> --json jobs 2>&1 | python3 -c "
import json, sys
data = json.load(sys.stdin)
for job in data.get('jobs', []):
    if job.get('conclusion') == 'failure':
        print(f'FAILED: {job[\"name\"]}')
"
```

### Step 2: Check if failures are in test groups related to the changes

Key question: **Do the failing test groups cover files touched by the PR?**

```bash
# See what the PR actually changed
git show <commit-hash> --stat

# For each failing test group, check what test files it covers
grep -A3 '"<Failing Job Name>"' .github/workflows/comprehensive-tests.yml
```

If failing jobs test files completely unrelated to the PR diff → strong flakiness signal.

### Step 3: Compare against last successful main branch run

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

### Step 4: Inspect the crash type

```bash
# Get detailed crash output
gh run view <run-id> --log-failed 2>&1 | grep -E "<Job Name>.*FAILED|<Job Name>.*crash|<Job Name>.*error" | head -20
```

**Runtime crash signatures:**
- `error: execution crashed` — Mojo runtime segfault, usually in `libKGENCompilerRTShared.so`
- Stack traces with only library frames (no user code) — infrastructure issue
- Crash before any test output — crash in static initialization or first function call

**Introduced regression signatures:**
- `error: compilation failed` — our code broke the build
- Test-specific failure messages — our code logic is wrong
- Crash only in tests that directly call new methods

### Step 5: Re-run failed jobs to confirm flakiness

```bash
gh run rerun <run-id> --failed
```

Wait for completion, then check results:

```bash
# After re-run completes
gh run view <run-id> --json jobs 2>&1 | python3 -c "
import json, sys
data = json.load(sys.stdin)
failures = [j for j in data.get('jobs', []) if j.get('conclusion') == 'failure']
print('FAILURES:', [j['name'] for j in failures])
"
```

**Verdict:**
- If previously failing jobs now pass → **flaky CI**, no code fix needed
- If failures persist with same crashes → **investigate root cause** in PR changes
- If only pre-existing failures remain (known broken tests on main) → **PR is clean**

### Step 6: Confirm new-method tests pass

Always verify the tests specific to the new functionality passed:

```bash
# Find which CI job covers the new test file
grep -B2 -A5 "<test_file_name>" .github/workflows/comprehensive-tests.yml

# Check that job's result
gh run view <run-id> --json jobs | python3 -c "..." | grep "<Job Name>"
```

## Results & Parameters

### Example: ExTensor utility methods PR (#2722)

**Scenario**: PR added `__str__`, `__hash__`, `contiguous()` etc. to ExTensor. CI showed:
- `Core Tensors` FAILED — crashes in `test_tensors.mojo`, `test_arithmetic.mojo`, etc.
- `Core Initializers` FAILED
- `Shared Infra` FAILED (one test, pre-existing)

**Analysis**:
- `test_tensors.mojo` does NOT use any new methods (`grep` confirmed zero references)
- Last successful main run (run ID `21873211512`) had Core Tensors: SUCCESS
- Crash type: `error: execution crashed` with only Mojo runtime library frames
- `Core Utilities` (which contains `test_utility.mojo`) PASSED — new methods work

**Re-run result**: Core Tensors and Core Initializers both PASSED on re-run. Only
`test_serialization.mojo` in Shared Infra remained failed — confirmed pre-existing on main.

**Verdict**: Flaky CI environment crashes, not caused by PR changes.

### Diagnostic Decision Tree

```
CI job fails on PR
    |
    v
Is the failing job's test files touched by the PR diff?
    |
    YES -> Likely introduced regression. Debug specific test.
    NO  -> Check last successful main run
            |
            Same jobs passed on main? -> Re-run CI
                |
                Re-run passes? -> Flaky CI, no fix needed
                Re-run fails?  -> Infrastructure problem, check with team
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Analyzing crash stack traces directly | Tried to identify crash cause from `libKGENCompilerRTShared.so` frame addresses | Stack frames are in stripped libraries with no symbols — no useful info | Runtime crashes in Mojo stdlib libs are not debuggable without symbolicated builds |
| Checking if `__str__` conformance causes issues | Hypothesized adding `__str__` changes Mojo trait resolution and causes downstream crashes | Could not confirm — tests that don't call `__str__` still crashed | Cannot infer crash cause from Mojo trait changes without being able to run the code locally |
| Comparing crash timestamps to identify common cause | Looked for timing correlation between crashes | Multiple crashes happened in parallel jobs — no useful pattern | Parallel CI jobs don't share state; crashes in unrelated jobs indicate infrastructure flakiness |
| Waiting for CI to complete before re-running | First attempt was to fully analyze before re-running | Wasted time on inconclusive analysis | Re-run should be triggered early as the fastest flakiness signal |
