---
name: reenable-flaky-ci-test-group
description: 'Re-enable a CI test group disabled as flaky by verifying historical
  pass before re-enabling. Use when: (1) test group commented out with ''flaky'' note,
  (2) crashes appear intermittent not consistent, (3) no code changes after last passing
  run.'
category: ci-cd
date: 2026-03-04
version: 1.0.0
user-invocable: false
---
# Re-enable Flaky CI Test Group

## Overview

| **Aspect** | **Details** |
|------------|-------------|
| **Date** | 2026-03-04 |
| **Objective** | Investigate and re-enable Core Loss test group (test_losses, test_loss_funcs, test_loss_utils) that was disabled for "flaky" crashes in Mojo CI |
| **Outcome** | Tests re-enabled after confirming they passed in historical CI run at sha `76dd17e9` with no subsequent code changes |
| **Issue** | #3120 |
| **PR** | #3223 |

## When to Use

Use this skill when:

- A CI test group is commented out in a workflow YAML with a note like `# DISABLED: Flaky tests`
- The issue description says tests "crash" but uses the word "flaky" (intermittent)
- You need to determine if the crash is a real code bug vs. transient runtime noise
- Test files were excluded from coverage validation scripts alongside the CI disable

**Trigger Patterns**:

- `# DISABLED: Flaky tests - see issue #XXXX` in GitHub Actions workflow matrix
- Corresponding exclusions in `validate_test_coverage.py` or similar scripts
- Issue body mentions "execution crashed" in Mojo tests

## Verified Workflow

### Step 1: Verify the disable commit

```bash
git log --oneline | grep -i "disable\|flaky\|DISABLED"
# Identify the commit that disabled the tests
git show <disable-commit> --stat
```

### Step 2: Find CI runs from before the disable

```bash
# List runs sorted by date, look for ones before the disable commit date
gh run list --workflow=comprehensive-tests.yml --branch main --limit 50 --json databaseId,headSha,conclusion,createdAt > /tmp/runs.json
python3 -c "
import json
runs = json.load(open('/tmp/runs.json'))
for r in runs:
    print(r['databaseId'], r['conclusion'], r['createdAt'][:16], r['headSha'][:8])
"
```

### Step 3: Check if test group passed in an earlier run

```bash
# For each candidate run, check its jobs
gh run view <run-id> --json jobs > /tmp/jobs.json
python3 -c "
import json
jobs = json.load(open('/tmp/jobs.json'))['jobs']
for j in jobs:
    if 'Loss' in j['name'] or 'loss' in j['name']:
        print(j['name'], j['conclusion'])
"
```

### Step 4: Verify no code changes after the last passing run

```bash
# Find the sha of the passing run
gh run view <passing-run-id> --json headSha
# Then check for relevant code changes after that sha
git log --oneline <passing-sha>..HEAD -- shared/core/loss*.mojo tests/shared/core/test_loss*.mojo
```

If no output: the implementation hasn't changed — the crashes were runtime flakiness.

### Step 5: Re-enable in comprehensive-tests.yml

Edit the workflow to uncomment the disabled test group:

```yaml
# Before (disabled):
# DISABLED: Flaky tests - see issue tracking Core Loss test crashes
# - name: "Core Loss"
#   path: "tests/shared/core"
#   pattern: "test_losses.mojo test_loss_funcs.mojo test_loss_utils.mojo"

# After (re-enabled):
- name: "Core Loss"
  path: "tests/shared/core"
  pattern: "test_losses.mojo test_loss_funcs.mojo test_loss_utils.mojo"
```

### Step 6: Remove exclusions from coverage validation

```python
# In scripts/validate_test_coverage.py, remove the block like:
# Exclude flaky Core Loss tests (see issue #3120)
# These tests crash consistently and are disabled until root cause is found
exclude_flaky_tests = [
    "tests/shared/core/test_losses.mojo",
    ...
]
exclude_files.extend(exclude_flaky_tests)
```

### Step 7: Commit and create PR

```bash
git add .github/workflows/comprehensive-tests.yml scripts/validate_test_coverage.py
git commit -m "fix(tests): re-enable Core Loss test group in CI

Investigation shows tests passed in CI run at sha <sha>.
No code changes after that passing run. Crashes were flaky
Mojo runtime noise, not code bugs.

Closes #XXXX"
git push -u origin <branch>
gh pr create --title "fix(tests): re-enable Core Loss test group in CI" ...
gh pr merge --auto --rebase <pr-number>
```

## Key Diagnostic: Distinguishing Flaky vs. Real Bug

| Signal | Interpretation |
|--------|---------------|
| Tests **passed** in at least one historical CI run | Likely flaky runtime — safe to re-enable |
| Tests **never** passed in any CI run | Likely real code bug — investigate implementation |
| "execution crashed" in Mojo (not assertion failure) | Runtime crash, often transient |
| No code changes to implementation since last passing run | Runtime environment issue, not code regression |
| Multiple different test groups show "execution crashed" | Systemic runner/Mojo issue, not test-specific |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Run tests locally | Tried `pixi run mojo test tests/shared/core/test_loss_utils.mojo` | GLIBC version mismatch — Mojo requires GLIBC_2.32+ but dev host had older version | Always check GLIBC version before trying to run Mojo tests locally; use CI for validation |
| Look for crash in "failing" CI run | Checked `21806302539` (Feb 8 22:10) for Core Loss crash logs | That run was after the disable commit — Core Loss was already commented out | Match CI run sha to git log to confirm test was actually enabled during that run |
| Search for code bug in loss.mojo | Reviewed bool mask casting, gradient checker memory management, copy semantics | Implementation was correct: `check_gradient` uses `_deep_copy` correctly, bool→dtype casts properly done | Sometimes the right fix is re-enabling, not patching |

## Results & Parameters

**Files changed:**

```
.github/workflows/comprehensive-tests.yml  (3 lines net change: 4 commented → 3 active)
scripts/validate_test_coverage.py          (9 lines removed: exclusion block)
```

**Verification method:**

```bash
gh run list --workflow=comprehensive-tests.yml --branch main --limit 50 \
  --json databaseId,headSha,conclusion,createdAt > /tmp/runs.json
```

Then cross-reference each `headSha` with `git log` to find runs before/after the disable commit.

**CI run that confirmed passing:** `21799938615` at sha `76dd17e9` (Jan 27 2026)

**Commits that disabled tests:**

- `d53d135e` — disabled in comprehensive-tests.yml
- `f701a8eb` — excluded from validate_test_coverage.py
