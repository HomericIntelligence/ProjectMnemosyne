# Session Notes: workflow-smoke-tests

## Session Context

- **Date**: 2026-03-07
- **Issue**: ProjectOdyssey #3318
- **PR**: ProjectOdyssey #3945
- **Branch**: `3318-auto-impl`
- **Follow-up from**: #3143 (fix-security-scan-gaps)

## Objective

Add automated regression tests to prevent recurrence of the security workflow gaps fixed in #3143:
1. `pull_request` trigger missing from security.yml
2. Semgrep step had `continue-on-error: true` (silencing SAST failures)
3. Gitleaks used `--no-git` (bypassing git history scan)

## What Was Done

### Workflow Fix

Removed `--no-git` from both Gitleaks invocations in `security.yml` (the remaining gap
not yet fixed by #3143 — the PR/push trigger and Semgrep were already correct).

### Smoke Tests (7 assertions)

`tests/smoke/test_security_workflow_properties.py`:
- `TestSecurityWorkflowTriggers::test_pull_request_trigger_present`
- `TestSecurityWorkflowTriggers::test_push_trigger_present`
- `TestSemgrepStep::test_semgrep_has_no_continue_on_error`
- `TestSemgrepStep::test_semgrep_action_used`
- `TestGitleaksStep::test_gitleaks_has_no_no_git_flag`
- `TestGitleaksStep::test_gitleaks_present`
- `TestGitleaksStep::test_gitleaks_has_exit_code`

All pass in ~0.02s after pixi environment loads.

### CI Workflow

`.github/workflows/workflow-smoke-test.yml` — triggers on all PRs. Design:
1. Fast grep checks (no pixi) — fail in 30s if regression present
2. Full pytest run (with pixi) — comprehensive assertions

### Pre-commit Hook

`.pre-commit-config.yaml` — pygrep hook:
```yaml
- id: check-security-workflow-no-git
  entry: 'gitleaks detect.*\-\-no\-git'
  language: pygrep
  files: ^\.github/workflows/security\.yml$
```

## Failure Log

### Attempt 1: `entry: '--no-git'` in pygrep hook

```
pre_commit.languages.pygrep: error: unrecognized arguments: --no-git
```

Root cause: pre-commit splits `entry` on spaces and passes tokens as CLI args.
`--no-git` is interpreted as a flag to the pygrep runner, not as the pattern.
Fix: use `gitleaks detect.*\-\-no\-git` to anchor with context.

### Attempt 2: `pixi run pytest` as pre-commit hook entry

Pre-commit reported "files were modified by this hook" because running pytest
causes Python to write/update `tests/__pycache__/__init__.cpython-314.pyc` (a
tracked file in the repo). pre-commit detects the modification and fails the commit
even though the tests themselves passed.

The tracked `.pyc` file is a pre-existing issue (should be in `.gitignore` and
removed from the index), but fixing that is out of scope.

Fix: Use pygrep for pre-commit (no side effects); use pytest only in CI.

### Attempt 3: `negate: true` on pygrep hook

```
[WARNING] Unexpected key(s) present on local => check-security-workflow-no-git: negate
```

`negate` is not a valid pre-commit key for pygrep hooks. The hook was silently
skipped after the warning. pygrep has no built-in negation — you have to either
flip the pattern or use a shell hook with `grep -v`.

## Key Insight: pygrep for Pre-commit vs pytest for CI

| Tool | Best for | Avoid for |
| ------ | ---------- | ----------- |
| pygrep hook | "Pattern X must NOT exist" (fast, no side effects) | Positive assertions ("must exist"), complex logic |
| pytest in CI | Both positive and negative, complex regex, multi-file | Pre-commit (slow startup, side effects from .pyc writes) |
| Shell steps in CI workflow | Quick sanity checks before expensive setup | Complex multi-line logic |
