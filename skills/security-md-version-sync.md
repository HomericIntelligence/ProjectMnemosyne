---
name: security-md-version-sync
description: "Keep SECURITY.md supported versions table in sync with pyproject.toml release version. Use when: (1) a new version is released and SECURITY.md still lists the old version, (2) an audit flags outdated supported versions, (3) you are bumping the project version in pyproject.toml."
category: documentation
date: 2026-03-25
version: "1.0.0"
user-invocable: false
verification: verified-precommit
tags:
  - security
  - versioning
  - documentation
  - audit
  - SECURITY.md
---

# SECURITY.md Version Sync

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-03-25 |
| **Objective** | Ensure SECURITY.md supported versions table reflects the current release version from pyproject.toml |
| **Outcome** | Successful — SECURITY.md updated to include 0.4.x as supported, PR created |
| **Verification** | verified-precommit |

## When to Use

- A new version has been released (pyproject.toml bumped) but SECURITY.md still lists the previous version
- An audit or review flags that SECURITY.md supported versions are outdated
- You are performing a version bump and want to ensure all version-referencing files are updated
- Users report confusion about whether their version receives security support

## Verified Workflow

> **Note:** Verified at pre-commit level — no unit tests needed for this documentation-only change.

### Quick Reference

```bash
# 1. Check current version
grep 'version' pyproject.toml | head -1
# 2. Check SECURITY.md table
grep -A5 'Supported Versions' SECURITY.md
# 3. Add new version row to SECURITY.md table
# 4. Run pre-commit hooks
pre-commit run --all-files
```

### Detailed Steps

1. **Check the canonical version** in `pyproject.toml` — the `[project].version` field is the single source of truth.

2. **Compare with SECURITY.md** — look at the supported versions table. If the current major.minor.x is missing, it needs updating.

3. **Update the table** — add the new version row at the top of the table. Keep the previous version as supported unless there's a specific reason to drop it. The table should list:
   - Current release series: `Yes`
   - Previous release series: `Yes` (unless explicitly EOL)
   - Older versions: `No`

4. **Run pre-commit hooks** — `pre-commit run --all-files` to verify markdown formatting is clean.

5. **Commit with conventional format** — `docs(security): add X.Y.x to supported versions table`

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| N/A — first implementation | Direct table edit in SECURITY.md | Did not fail | Simple documentation edits are low-risk; no tests needed beyond pre-commit hooks |

## Results & Parameters

### SECURITY.md Table Pattern

```markdown
| Version | Supported |
|---------|-----------|
| 0.4.x   | Yes       |
| 0.3.x   | Yes       |
| < 0.3   | No        |
```

### Version Support Policy

- Current release series (matching `pyproject.toml` version): always supported
- Previous release series: supported unless explicitly EOL'd
- Two or more releases behind: not supported
- Use `X.Y.x` wildcard notation (e.g., `0.4.x`) to cover all patch versions in a series

### Commit Message Template

```
docs(security): add X.Y.x to supported versions table

Closes #<issue-number>
```

### Automation Opportunity

This could be automated as part of a release workflow — when `pyproject.toml` version is bumped, a CI step could verify SECURITY.md includes the new version. The existing `versioning-consistency-release-workflow` skill covers `pyproject.toml`/`pixi.toml`/`__init__.py` consistency but does not yet check SECURITY.md.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectHephaestus | Issue #47 — Audit S8 Security: SECURITY.md outdated | PR #76: 1 file changed, added 0.4.x row to supported versions table |
