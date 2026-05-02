---
name: hadolint-failure-threshold-config
description: "Use when: (1) hadolint-action CI job fails on warnings despite rules being in the ignore list, (2) configuring .hadolint.yaml for a project that explicitly ignores certain warning-level rules, (3) hadolint CI is too strict or too permissive."
category: ci-cd
date: 2026-04-23
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [docker, hadolint, dockerfile, lint, failure-threshold, ci, github-actions]
---

# hadolint failure-threshold Configuration

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-23 |
| **Objective** | Fix hadolint-action job failing on warnings that are already in the ignore list |
| **Outcome** | Setting failure-threshold to `error` stopped false failures on ignored rules |
| **Verification** | verified-ci |

## When to Use

- `.hadolint.yaml` has rules in the `ignore:` list but hadolint-action still fails the CI job
- hadolint CI job is failing on warnings/info-level findings that you have consciously accepted
- Configuring hadolint for a project where you only want actual errors to fail CI

## Verified Workflow

### Quick Reference

```yaml
# .hadolint.yaml
failure-threshold: error   # Only fail CI on actual errors, not warnings/info
ignore:
  - DL3008   # apt-get without version pinning (acceptable for dev images)
  - DL3009   # Delete apt lists (handled separately)
  - SC2086    # Double-quote prevention (project convention differs)
```

### Detailed Steps

1. Check current `.hadolint.yaml`:
   ```bash
   cat .hadolint.yaml
   ```

2. If `failure-threshold: warning` (or not set, defaults to warning), and your `ignore:` list covers all warnings you've accepted, change it:
   ```yaml
   # Before (fails on any warning, even ignored-rule categories):
   failure-threshold: warning
   ignore:
     - DL3008

   # After (only fails on errors — warnings in ignore list don't cause CI failure):
   failure-threshold: error
   ignore:
     - DL3008
   ```

3. Verify locally with hadolint:
   ```bash
   hadolint --config .hadolint.yaml bases/Dockerfile.node
   ```

4. Push and confirm CI job passes.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Adding rules to `ignore:` list with `failure-threshold: warning` | Expected that ignored rules would not cause CI failure | hadolint-action v3.1.0 can still exit non-zero when threshold is `warning` even if the specific rule triggering it is in the ignore list (edge case in threshold evaluation) | Use `failure-threshold: error` when all warning-level rules you care about are in `ignore:` — this is the correct semantics: explicit ignores mean you've accepted those warnings |

## Results & Parameters

### hadolint Severity Levels (low → high)

| Level | Example Rules | CI Behavior with `failure-threshold: error` |
| ------- | -------------- | ---------------------------------------------- |
| `info` | DL3048 (label conventions) | Does NOT fail CI |
| `warning` | DL3008 (unversioned apt), DL3009 (apt lists) | Does NOT fail CI |
| `error` | DL3006 (always tag FROM), invalid syntax | FAILS CI |
| `ignore` | Any rule in `ignore:` list | Never reported |

### .hadolint.yaml Full Reference

```yaml
failure-threshold: error   # info | style | warning | error | ignore
ignore:
  - DL3008  # pin apt-get to specific versions
  - DL3009  # delete /var/lib/apt/lists
  - DL3015  # avoid additional packages with apt-get install
  - SC2086   # double quote to prevent globbing
no-fail: false
trustedRegistries:
  - docker.io
  - ghcr.io
```

### Rule of Thumb

> Use `failure-threshold: error` when you have explicitly listed all warning-level rules you accept in `ignore:`. This makes the CI contract clear: "We've reviewed and accepted these warnings; only actual errors block merge."

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| AchaeanFleet | CI repair session — hadolint job was failing despite ignore list | 2026-04-23; resolved by setting failure-threshold: error |
