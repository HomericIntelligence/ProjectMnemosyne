---
name: pr-ci-failure-triage
description: 'Triage and fix CI failures blocking PR merges in Mojo/GitHub Actions
  projects. Use when: multiple PRs stuck with CI failures, pre-commit markdownlint
  or action SHA errors, Mojo --Werror unused return value errors.'
category: ci-cd
date: 2026-03-14
version: 1.0.0
user-invocable: false
---
## Overview

| Attribute | Value |
|-----------|-------|
| **Category** | ci-cd |
| **Complexity** | Medium-High |
| **Time** | 30–90 min for multiple PRs |
| **Prerequisites** | `gh` CLI auth, git access to repo |

Systematic approach to unblock multiple stuck PRs by diagnosing CI failures, applying targeted
fixes, and rebasing branches. Key insight: distinguish between PR-specific failures vs baseline
failures that exist on `main` itself (don't fix what main already has broken).

## When to Use

- Multiple open PRs all showing CI failures preventing auto-merge
- `pre-commit` checks fail on markdown or workflow files
- GitHub Actions workflows fail with "invalid SHA" or "unknown action" errors
- Mojo compilation fails with `unused return value` under `--Werror`
- Test files were split (ADR-009 pattern) but CI workflows still reference old monolithic filenames

## Verified Workflow

### Quick Reference

```bash
# Check all open PRs
gh pr list --state open

# Check CI status for a specific PR
gh pr checks <pr-number>

# Check required vs optional checks
gh api repos/<owner>/<repo>/branches/main/protection/required_status_checks

# Rebase PR branch onto main
git fetch origin && git rebase origin/main <branch-name>
git push --force-with-lease origin <branch-name>
```

### Step 1: Identify Required Checks

Before fixing anything, determine which CI checks are *required* for merge vs optional.

```bash
gh api repos/<owner>/<repo>/branches/main/protection/required_status_checks \
  --jq '.contexts[]'
```

**Critical insight**: Only fix failures in required checks. Optional checks (e.g., benchmarks,
performance tests) will not block merging even if they fail.

### Step 2: Triage Each PR

For each blocked PR, run:

```bash
gh pr checks <pr-number> --watch
```

Categorize each failure as:

- **PR-specific** — only fails on this branch, not on `main`
- **Baseline failure** — also fails on `main`; skip fixing (not this PR's problem)
- **Infrastructure** — invalid action SHAs, missing files, workflow syntax errors

### Step 3: Fix Pattern — pre-commit markdownlint Exclusions

**Symptom**: `markdownlint-cli2` fails on files that should be excluded (e.g., `.claude/plugins/`).

**Wrong fix**: Adding paths to `.markdownlintignore` — pre-commit hooks do NOT read this file.

**Correct fix**: Edit the `exclude:` regex in `.pre-commit-config.yaml` for the
`markdownlint-cli2` hook:

```yaml
# Before
- repo: https://github.com/DavidAnson/markdownlint-cli2
  hooks:
    - id: markdownlint-cli2
      exclude: ^notes/(plan|issues|review|blog)/

# After
- repo: https://github.com/DavidAnson/markdownlint-cli2
  hooks:
    - id: markdownlint-cli2
      exclude: ^(notes/(plan|issues|review|blog)|\.claude/plugins)/
```

### Step 4: Fix Pattern — Invalid Pinned Action SHAs

**Symptom**: GitHub Actions workflow fails with `Error: Could not find actions/checkout@<sha>`.

**Cause**: SHA used for a pinned action doesn't correspond to the stated version comment.

**Fix**: Cross-reference valid SHAs from other workflow files in the repo:

```bash
grep -r "actions/checkout@" .github/
grep -r "actions/cache@" .github/
```

Use the SHA that appears most frequently (or is confirmed correct by other passing workflows).

| Action | Version | Confirmed SHA |
|--------|---------|---------------|
| `actions/checkout` | v4 | `8e8c483db84b4bee98b60c0593521ed34d9990e8` |
| `actions/cache` | v5 | `cdf6c1fa76f9f475f3d7449005a359c84ca0f306` |

### Step 5: Fix Pattern — Split Test Files (ADR-009)

**Symptom**: CI workflow runs `just test-group "path" "test_foo.mojo"` but the file was split
into `test_foo_part1.mojo` and `test_foo_part2.mojo`.

**Cause**: ADR-009 pattern splits test files exceeding 10 `fn test_` functions. CI workflows
and `run_all_tests.mojo` import collectors must be updated together.

**Fix locations** (must update all three):

1. GitHub Actions workflow file (`.github/workflows/test-*.yml`):

   ```yaml
   # Before
   just test-group "tests/path/samplers" "test_sequential.mojo"
   # After
   just test-group "tests/path/samplers" "test_sequential_part1.mojo test_sequential_part2.mojo"
   ```

2. `run_all_tests.mojo` imports:

   ```mojo
   # Before
   from tests.shared.data.samplers.test_sequential import (...)
   # After
   from tests.shared.data.samplers.test_sequential_part1 import (...)
   ```

3. `comprehensive-tests.yml` matrix (if applicable):

   ```yaml
   # Before
   test_unsigned.mojo
   # After
   test_unsigned_part2.mojo test_unsigned_part3.mojo
   ```

### Step 6: Fix Pattern — Mojo `--Werror` Unused Return Values

**Symptom**: `error: unused return value` in benchmark or test files.

**Cause**: Mojo functions returning `Tuple` or `ExTensor` — even benchmark `step` functions —
must have their return value explicitly discarded when `--Werror` is enabled.

**Fix**: Prefix bare calls with `_ =`:

```mojo
# Before (compile error under --Werror)
sgd_step(model, grads, lr)
adam_step(model, grads, lr, m, v, t)

# After
_ = sgd_step(model, grads, lr)
_ = adam_step(model, grads, lr, m, v, t)
```

**Detection**: Search for functions that return `Tuple` and are called without assignment:

```bash
grep -n "sgd_step\|adam_step\|fn.*-> Tuple" tests/shared/benchmarks/
```

### Step 7: Rebase and Force Push

After fixes are committed on the feature branch:

```bash
git fetch origin
git rebase origin/main
git push --force-with-lease origin <branch-name>
```

If rebase has conflicts from cherry-picked commits already in main:

```bash
git rebase --reapply-cherry-picks origin/main
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Added paths to `.markdownlintignore` | Expected pre-commit hook to read the ignore file | pre-commit's markdownlint-cli2 hook uses `args:` config, not `.markdownlintignore` | Always use `exclude:` regex in `.pre-commit-config.yaml` to exclude files from hooks |
| Used `git checkout <branch>` to switch branches | Expected standard git checkout | Safety Net hook blocked `git checkout` for branch switching | Use `git switch <branch>` instead of `git checkout <branch>` for switching |
| Used `git branch -D <branch>` to delete merged branch | Standard force-delete | Safety Net blocked `-D` (force delete) | Use `git branch -d <branch>` (safe delete that requires merge) |
| Fixed PR #4510 by rebasing with new commits | Branch had commits already squash-merged into main | Rebase produced diverged history with duplicate content | Check if branch content already exists in main via `git log origin/main..<branch>` before rebasing; close as superseded if already merged |
| Tried to fix baseline failures on PRs | Failures appeared on PR CI | Same failures existed on `main` — not PR-specific | Always check `main` CI status first; don't attempt to fix inherited baseline failures in PR branches |

## Results & Parameters

### Required CI Checks (ProjectOdyssey)

```text
- pre-commit
- security-report
- Mojo Package Compilation
- Code Quality Analysis
- secret-scan
```

Benchmark and performance checks are NOT required — failures there don't block merge.

### Rebase Command for Cherry-Pick Conflicts

```bash
git rebase --reapply-cherry-picks origin/main
```

### pre-commit Config Exclusion Pattern

```yaml
# Exclude multiple directory patterns
exclude: ^(notes/(plan|issues|review|blog)|\.claude/plugins)/
```

### Mojo Unused Return Fix Template

```bash
# Find all bare calls to functions returning Tuple
grep -n "^\s*sgd_step\|^\s*adam_step\|^\s*<fn_name>" <file>
# Add "_ = " prefix to each
sed -i 's/^    sgd_step/    _ = sgd_step/g' <file>
```
