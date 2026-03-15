---
name: training-tests-weekly-workflow
description: "Create a weekly GitHub Actions workflow for Mojo training tests excluded from per-PR CI. Use when: test files are in validate_test_coverage.py exclusion list but have no periodic workflow running them."
category: ci-cd
date: 2026-03-15
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Problem** | Training/slow test files excluded from per-PR CI become silently untested unless a separate periodic workflow covers them |
| **Solution** | Create a weekly GitHub Actions workflow that runs all files in `tests/shared/training/` (or similar excluded directories) |
| **Key Insight** | The `validate_test_coverage.py` exclusion list is the source of truth — if a file is excluded from PR CI, it MUST appear in a periodic workflow |
| **Scope** | One new workflow file; `validate_test_coverage.py` typically needs no changes if files are already in the exclusion list |
| **Verification** | `python scripts/validate_test_coverage.py` exits 0 + YAML syntax check |

## When to Use

- New test files were added to the `exclude_training_patterns` (or similar) list in `validate_test_coverage.py` without a corresponding weekly workflow
- Follow-up issue specifically asks to verify weekly E2E workflow covers excluded training tests
- `NOTE: Training tests moved to weekly workflow` comment exists in `comprehensive-tests.yml` but the weekly workflow was never created
- Any periodic workflow needs to be created to cover a batch of excluded test files

## Verified Workflow

### Quick Reference

```bash
# 1. Check existing weekly workflows
ls .github/workflows/*weekly*.yml

# 2. Verify test files ARE already in exclusion list
grep -n "test_checkpoint\|test_config" scripts/validate_test_coverage.py

# 3. Create the weekly workflow (see template below)
# Use action versions consistent with comprehensive-tests.yml

# 4. Validate
python scripts/validate_test_coverage.py  # must exit 0
pixi run pre-commit run check-yaml --files .github/workflows/training-tests-weekly.yml
```

### Step-by-Step

1. **Identify the gap**: Read the issue. Check `comprehensive-tests.yml` for `NOTE: ... moved to weekly workflow` comments. Confirm there is no `training-tests-weekly.yml` (or equivalent).

2. **Confirm exclusion list state**: The new test files should already be in the `exclude_training_patterns` list in `validate_test_coverage.py`. If they are, no changes to that file are needed.

3. **Identify action pin versions**: Read `comprehensive-tests.yml` to find the pinned SHA hashes for:
   - `actions/checkout@<sha>`
   - `extractions/setup-just@<sha>`
   - `actions/upload-artifact@<sha>`
   Use these same versions in the new workflow for consistency.

4. **Create the workflow file** at `.github/workflows/training-tests-weekly.yml`:

   ```yaml
   name: Weekly Training Tests

   # Weekly training tests that are excluded from per-PR CI
   # Runs every Sunday at 3 AM UTC (offset from simd-benchmarks-weekly at 2 AM)

   on:
     schedule:
       - cron: '0 3 * * 0'
     workflow_dispatch:

   permissions:
     contents: read

   jobs:
     training-tests:
       name: Training Unit Tests
       runs-on: ubuntu-latest
       timeout-minutes: 60
       if: github.event_name == 'workflow_dispatch' || github.ref == 'refs/heads/main'

       steps:
         - name: Checkout code
           uses: actions/checkout@<sha>  # v6.0.1

         - name: Set up Pixi
           uses: ./.github/actions/setup-pixi

         - name: Install Just
           uses: extractions/setup-just@<sha>  # v3

         - name: Run training tests
           run: just test-group tests/shared/training "test_*.mojo"

         - name: Upload test results
           if: always()
           uses: actions/upload-artifact@<sha>  # v7
           with:
             name: test-results-Training-Weekly
             path: test-results/
             retention-days: 30
   ```

5. **Verify**:
   ```bash
   python scripts/validate_test_coverage.py  # exit 0
   pixi run pre-commit run check-yaml --files .github/workflows/training-tests-weekly.yml
   ```

6. **Commit and PR**: Single-file change. Link `Closes #<issue>` in commit and PR body.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Adding test files to `comprehensive-tests.yml` | Initially considered adding 9 new files directly to PR CI matrix | Training tests are excluded from PR CI intentionally (slow/dataset-dependent); adding them back breaks the design | Always check WHY files were excluded before deciding where to add coverage |
| Modifying `validate_test_coverage.py` | Considered adding 9 files to exclusion list as part of this change | Files were already in the exclusion list — the gap was the missing workflow, not the validator | Always check if exclusion list already contains the files before editing it |

## Results & Parameters

### Cron Schedule Offset Pattern

Offset weekly workflows from each other to avoid resource contention:

| Workflow | Schedule | Time |
|----------|----------|------|
| `simd-benchmarks-weekly.yml` | `0 2 * * 0` | Sunday 2 AM UTC |
| `training-tests-weekly.yml` | `0 3 * * 0` | Sunday 3 AM UTC |

### Key Decisions

- **`timeout-minutes: 60`**: Training tests can be slow; generous timeout prevents false failures
- **`retention-days: 30`**: Weekly artifacts don't need 1-year retention (unlike benchmark trend data)
- **`if: ... || github.ref == 'refs/heads/main'`**: Scheduled runs only on main; `workflow_dispatch` allows any branch for debugging
- **`permissions: contents: read`**: Minimal permissions — no PR write needed
