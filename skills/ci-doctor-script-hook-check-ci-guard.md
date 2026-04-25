---
name: ci-doctor-script-hook-check-ci-guard
description: "Shell doctor/health-check scripts that verify local developer setup (git hooks, SSH keys, local config files) must guard against CI environments where that infrastructure doesn't exist. Use when: (1) a doctor.sh CI job fails because .git/hooks/ doesn't exist on GitHub Actions runners, (2) any check_*() function in a health-check script validates developer-local resources that are absent in CI, (3) writing new doctor script checks that should only run locally, (4) debugging CI failures where a health/preflight script exits 1 due to missing local setup artifacts."
category: ci-cd
date: 2026-04-25
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - ci
  - doctor
  - shell
  - git-hooks
  - github-actions
  - health-check
  - ci-guard
  - environment-detection
---

# CI Doctor Script Hook-Check Guard

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-25 |
| **Objective** | Fix CI failure where `scripts/doctor.sh` "Check 4: Git hooks" exited 1 because GitHub Actions runners lack `.git/hooks/` infrastructure |
| **Outcome** | Added `${CI:-}` guard to skip developer-local checks in CI; PR #350 (ProjectMyrmidons) passed |
| **Verification** | verified-ci |

## When to Use

- A CI job runs `just doctor` (or equivalent) and fails at a git-hooks check
- A `check_hooks()` or similar function in a health-check script references `.git/hooks/` paths that don't exist in CI
- Writing any new doctor/preflight check that validates developer-local setup (hooks, SSH agent, local config, pre-commit installations)
- A GitHub Actions job exits 1 with errors like "pre-commit hook not installed" or "pre-commit hook not executable" from a health-check script
- Deciding whether a check should be skipped silently in CI or should error

## Verified Workflow

### Quick Reference

```bash
# Standard CI guard pattern for any developer-local check function:
if [[ "${CI:-}" == "true" ]]; then
    warn "check skipped in CI" "reason: <why this is dev-local only>"
    return
fi
```

### Detailed Steps

1. **Identify the failing check function** — Find the `check_*()` function in the doctor script that references local developer artifacts (`.git/hooks/`, `~/.ssh/`, `.pre-commit-config.yaml` install state, etc.).

2. **Understand the CI context** — GitHub Actions automatically sets `CI=true` in all runner environments. The `${CI:-}` form safely handles both set (`CI=true`) and unset (local shell) cases without erroring on `set -u` shells.

3. **Add the guard at the TOP of the check function**, before any file existence tests:

   ```bash
   check_hooks() {
       section "Check N: Git hooks"

       local hook_src="${REPO_ROOT}/hooks/pre-commit"
       local hook_dst="${REPO_ROOT}/.git/hooks/pre-commit"

       if [[ ! -f "$hook_src" ]]; then
           warn "hooks/pre-commit source not found in repo"
           return
       fi

       # In CI there is no .git/hooks directory; skip this check silently.
       if [[ "${CI:-}" == "true" ]]; then
           warn "pre-commit hook check skipped in CI" "hooks are installed by developers locally"
           return
       fi

       if [[ ! -f "$hook_dst" ]]; then
           fail "pre-commit hook not installed" \
               "Run: just install-hooks"
       elif [[ ! -x "$hook_dst" ]]; then
           fail "pre-commit hook not executable" \
               "Run: chmod +x .git/hooks/pre-commit"
       else
           pass "pre-commit hook installed and executable"
       fi
   }
   ```

4. **Use `warn` not `pass`** for the CI skip message — this makes it visible in CI logs that the check was intentionally skipped, rather than silently omitted.

5. **Test locally** that the guard doesn't suppress the check in a normal developer shell (`CI` is not set locally unless the developer has it in their environment).

6. **Verify in CI** — Push the fix and confirm the doctor CI job exits 0.

### General Pattern for All Developer-Local Checks

Any check that validates local developer environment setup should follow this template:

```bash
check_<name>() {
    section "Check N: <description>"

    # Skip checks that require local developer environment setup in CI.
    if [[ "${CI:-}" == "true" ]]; then
        warn "<check name> skipped in CI" "<brief reason>"
        return
    fi

    # ... rest of check logic
}
```

**Categories of checks that need CI guards:**

| Check Type | Examples |
|------------|---------|
| Git hooks | `.git/hooks/pre-commit`, `.git/hooks/commit-msg` |
| SSH infrastructure | `~/.ssh/id_ed25519`, `ssh-agent` running |
| Local config files | `~/.netrc`, `.env.local`, tool-specific dotfiles |
| Pre-commit install state | `pre-commit` installed and configured |
| GPG signing setup | GPG keys, git `user.signingkey` |
| Editor/IDE config | `.editorconfig` compliance, IDE plugin installation |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| No failed attempts | The fix was straightforward once the root cause was identified | N/A | `actions/checkout` creates a minimal git repo without hook infrastructure — this is expected and by design |

## Results & Parameters

### Root Cause Summary

```
GitHub Actions `actions/checkout`:
  - Creates a shallow clone of the repository
  - Does NOT run `git init` hooks setup
  - Does NOT create .git/hooks/ directory
  - The .git/hooks/ directory only exists after a developer runs:
      pre-commit install
      OR
      just install-hooks
      OR
      git init (on a new repo)
```

### Environment Variable Reference

```bash
# GitHub Actions sets this automatically on all runners:
CI=true

# Safe access pattern (works with set -u):
${CI:-}          # Expands to empty string if CI is unset
${CI:-false}     # Expands to "false" if CI is unset

# Recommended guard:
if [[ "${CI:-}" == "true" ]]; then
    # CI environment: skip developer-local checks
fi
```

### Where This Guard Is Needed

The `.git/hooks/` directory is absent on:
- GitHub Actions runners (all OS: ubuntu, macos, windows)
- GitLab CI runners (shallow clones)
- Any CI system using `git clone --depth=1` or `actions/checkout`
- Docker-based CI where the repo is copied in rather than cloned

It IS present on:
- Developer machines that have run `pre-commit install`
- Full (non-shallow) clones where `git init` was run
- CI jobs that explicitly run `pre-commit install` as a step (but then the hook exists, so the check passes)

### Verified Fix (ProjectMyrmidons doctor.sh)

```bash
# Before: check_hooks() called fail() if .git/hooks/pre-commit was missing
# → CI job exited 1 because actions/checkout does not create .git/hooks/

# After: guard added at top of function
if [[ "${CI:-}" == "true" ]]; then
    warn "pre-commit hook check skipped in CI" "hooks are installed by developers locally"
    return
fi
# → CI job passes; local developer runs still check for hook installation
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectMyrmidons | PR #350 | `scripts/doctor.sh` Check 4 was failing `just doctor --skip-connectivity` in CI. Added `${CI:-}` guard. CI job passed after fix. |
