---
name: fix-security-scan-gaps
description: 'Fix common GitHub Actions security scanning gaps: missing PR triggers,
  silenced Semgrep failures, and Gitleaks history blindness. Use when: (1) security
  scans only run on push to main, (2) Semgrep has continue-on-error masking failures,
  (3) Gitleaks uses --no-git missing history secrets.'
category: ci-cd
date: 2026-03-05
version: 1.0.0
user-invocable: false
---
# Fix Security Scan Gaps

## Overview

| Item | Details |
|------|---------|
| Date | 2026-03-05 |
| Objective | Fix three common security scanning gaps in GitHub Actions workflows |
| Outcome | Operational — applied in ProjectOdyssey PR #3315 (issue #3143) |

Addresses the three most common ways security workflows fail silently or miss issues before they reach main.

## When to Use

- Security scans only trigger on `push: branches: [main]` — not on PRs
- Semgrep step has `continue-on-error: true` so SAST failures are silently ignored
- Gitleaks runs with `--no-git` — scans only the working directory, missing secrets in git history
- Post-audit of a security workflow to verify it actually enforces on PRs
- Setting up a new security scanning workflow from scratch

## Verified Workflow

### Gap 1: Add PR trigger to security-scan.yml

```yaml
# BEFORE (only runs after merge to main):
on:
  push:
    branches:
      - main

# AFTER (runs on all PRs and pushes to main):
on:
  pull_request:

  push:
    branches:
      - main

  workflow_dispatch:
```

### Gap 2: Remove continue-on-error from Semgrep

```yaml
# BEFORE (failures silently ignored):
- name: Run Semgrep
  uses: returntocorp/semgrep-action@v1
  with:
    config: auto
    generateSarif: true
  continue-on-error: true

# AFTER (failures block the job and PR):
- name: Run Semgrep
  uses: returntocorp/semgrep-action@v1
  with:
    config: auto
    generateSarif: true
```

Note: `continue-on-error: true` on the **SARIF upload** step after Semgrep is acceptable —
the upload is a reporting step and should not block the scan result itself.

### Gap 3: Remove --no-git from Gitleaks

```bash
# BEFORE (scans working directory only — misses git history):
./gitleaks detect --source=. --verbose --no-git --exit-code=1

# AFTER (git log mode — scans full commit history):
./gitleaks detect --source=. --verbose --exit-code=1
```

The default Gitleaks mode (without `--no-git`) uses `git log` to scan the full history.
This requires `fetch-depth: 0` on the checkout step:

```yaml
- name: Checkout code
  uses: actions/checkout@...
  with:
    fetch-depth: 0  # Full history for comprehensive scanning
```

### Verification checklist

After applying fixes, verify:

```bash
# 1. Confirm pull_request trigger is present
grep -n "pull_request" .github/workflows/security-scan.yml

# 2. Confirm Semgrep step has NO continue-on-error
grep -A 6 "Run Semgrep" .github/workflows/security-scan.yml | grep "continue-on-error"
# Should return nothing

# 3. Confirm --no-git is gone from Gitleaks
grep "no-git" .github/workflows/security-pr-scan.yml
# Should return nothing

# 4. Validate YAML syntax
python3 -c "
import yaml, sys
for f in ['.github/workflows/security-scan.yml', '.github/workflows/security-pr-scan.yml']:
    yaml.safe_load(open(f))
    print(f'OK: {f}')
"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Remove all continue-on-error | Removed `continue-on-error` from every step in the file | SARIF upload and artifact download steps legitimately use it to prevent reporting failures from blocking scan results | Only remove `continue-on-error` from the scan step itself, not reporting/upload steps |
| Use `--log-opts` for PR diff only | Considered `--log-opts="HEAD~1..HEAD"` to limit Gitleaks to PR diff | Would miss secrets introduced earlier in the branch history | Default git log mode is safer; scans entire branch reachable history |

## Results & Parameters

Applied to ProjectOdyssey issue #3143, PR #3315:

- Files changed: `.github/workflows/security-scan.yml`, `.github/workflows/security-pr-scan.yml`
- Lines changed: 6 insertions, 3 deletions
- YAML validation: passed with Python `yaml.safe_load`

Key pattern: security workflows often have these gaps because they were initially set up
for reporting only (main branch), then `continue-on-error` was added to avoid blocking
pipelines during setup, and `--no-git` was added to make Gitleaks faster. All three
are technically functional but defeat the purpose of pre-merge security enforcement.

## References

- Gitleaks docs: `--no-git` flag disables git log scanning
- Semgrep Action: `continue-on-error` masks SAST failures from PR status checks
- GitHub Actions `pull_request` trigger: required for PR blocking checks
- ProjectOdyssey CLAUDE.md: security scanning policy
