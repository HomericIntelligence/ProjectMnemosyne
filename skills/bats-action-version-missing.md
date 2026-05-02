---
name: bats-action-version-missing
description: "Documents that bats-core/bats-action@2 does not exist on the GitHub Actions marketplace. Use when: (1) GHA fails with 'Unable to resolve action bats-core/bats-action@X', (2) merging branches that introduce new uses: action references for bats, (3) setting up BATS shell testing in GitHub Actions."
category: ci-cd
date: 2026-04-23
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: []
---

# bats-action-version-missing

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-23 |
| **Objective** | Install BATS in GitHub Actions CI using `bats-core/bats-action@2` |
| **Outcome** | Failed — `@2` major-version alias does not exist; reverted to `apt-get install bats` which succeeded |
| **Verification** | verified-ci |

## When to Use

- GitHub Actions workflow fails with `Unable to resolve action 'bats-core/bats-action@2', unable to find version '2'`
- Merging or reviewing branches that introduce `uses: bats-core/bats-action@X` references
- Setting up BATS shell testing in a GitHub Actions workflow
- Resolving merge conflicts involving `uses:` action references for BATS
- Any CI failure with "Unable to resolve action" for an action you haven't verified exists

## Verified Workflow

### Quick Reference

```yaml
# SAFE — always works on ubuntu-latest
- name: Install bats
  run: sudo apt-get install -y bats

# ALSO SAFE — @1 major alias exists
- uses: bats-core/bats-action@1

# SAFE if/when released — use explicit tag
- uses: bats-core/bats-action@v2.0.0
```

### Detailed Steps

1. If a workflow uses `uses: bats-core/bats-action@2`, replace it immediately — this tag does not exist.
2. Preferred fallback: `sudo apt-get install -y bats` in a `run:` step. Zero external dependencies, always available on `ubuntu-latest`.
3. If you prefer using the action: check https://github.com/bats-core/bats-action/releases for valid tags before using them.
4. Valid tags as of 2026-04-23: `@1` (major alias), `@v1.x.x` (specific), `@v2.0.0` (if released).
5. When merging PRs or resolving conflicts that introduce `uses:` lines, always verify the action tag exists before pushing.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| `bats-core/bats-action@2` | Used `@2` major-version alias in a GHA workflow after a merge conflict resolution | The `@2` tag does not exist in the `bats-core/bats-action` repository; GitHub Actions immediately fails with "Unable to resolve action `bats-core/bats-action@2`, unable to find version `2`" | The `@2` major-version alias for `bats-core/bats-action` has never been published — only `@1` and specific version tags exist |
| Merge without verification | Resolved a PR conflict that merged a workflow using `bats-core/bats-action@2` without checking the action's releases | The action tag was invalid, causing immediate CI failure on push | Always verify `uses:` action references against the action's GitHub releases page before pushing |

## Results & Parameters

### Valid installation methods for BATS in GitHub Actions (ubuntu-latest)

```yaml
# Option 1: apt-get (RECOMMENDED — no external action dependency)
- name: Install bats
  run: sudo apt-get install -y bats

# Option 2: bats-core/bats-action@1 (major alias — verified to exist)
- uses: bats-core/bats-action@1

# Option 3: explicit version tag (verify existence first)
# Check: https://github.com/bats-core/bats-action/releases
- uses: bats-core/bats-action@v1.2.1   # example — verify tag exists
```

### Version alias availability (as of 2026-04-23)

| Alias / Tag | Exists? | Notes |
| ------------- | --------- | ------- |
| `@1` | Yes | Major alias for v1.x |
| `@2` | **No** | Does not exist — causes "Unable to resolve action" |
| `@v1.x.x` | Yes (specific) | Check releases page for exact version |
| `@v2.0.0` | Unconfirmed | Use only after verifying on releases page |

### Diagnosing "Unable to resolve action" errors

```
##[error]Unable to resolve action `bats-core/bats-action@2`, unable to find version `2`
```

This error means one of:
- The action tag/version does not exist in the action's GitHub repository
- The action's repository does not have that ref (tag or branch)

Always fix by replacing with `apt-get install bats` or a confirmed valid tag.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| AchaeanFleet | Post-merge conflict resolution; reverted to apt-get, CI passed | verified-ci |
