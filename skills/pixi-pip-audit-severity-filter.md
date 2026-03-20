---
name: pixi-pip-audit-severity-filter
description: Configure pip-audit in pixi CI to fail only on HIGH/CRITICAL severity
  vulnerabilities using pixi task definitions
category: ci-cd
date: 2026-02-22
version: 1.0.0
user-invocable: false
---
# Skill: pixi-pip-audit-severity-filter

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-02-22 |
| Objective | Configure pip-audit in pixi CI to fail only on HIGH/CRITICAL severity vulnerabilities |
| Outcome | Success — pixi task definition approach avoids workflow YAML changes |
| Project | ProjectScylla |
| Issue | #874 |

## When to Use

Use this skill when:
- A pixi-based project uses `pip-audit` in CI and you need to filter by severity
- CI is blocking on LOW/MEDIUM vulnerabilities that have no available fix
- You want to apply pip-audit flags without modifying GitHub Actions workflow YAML
- pip-audit is invoked via `pixi run --environment <env> pip-audit`

## Verified Workflow

### 1. Bump pip-audit to >=2.8 in pixi.toml

`--min-severity` flag was added in pip-audit 2.8. Update the pypi-dependency:

```toml
[feature.lint.pypi-dependencies]
pip-audit = ">=2.8"
```

### 2. Add a named task in the feature's tasks section

The key insight: define the task in `[feature.<name>.tasks]` so that
`pixi run --environment <name> pip-audit` automatically applies severity filtering
without any changes to the GitHub Actions workflow YAML:

```toml
[feature.lint.tasks]
pip-audit = "pip-audit --min-severity high"
```

### 3. Verify the task resolves correctly

```bash
pixi run --environment lint pip-audit --version
# Output: ✨ Pixi task (pip-audit in lint): pip-audit --min-severity high --version
# pip-audit 2.10.0
```

The `✨ Pixi task` line confirms flags are baked in correctly.

### 4. (Optional) Add the workflow file to its own path triggers

```yaml
on:
  pull_request:
    paths:
      - "pixi.toml"
      - "pixi.lock"
      - ".github/workflows/security.yml"  # add this
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

### pixi.toml snippet (copy-paste ready)

```toml
[feature.lint.pypi-dependencies]
pip-audit = ">=2.8"

[feature.lint.tasks]
pip-audit = "pip-audit --min-severity high"
```

### GitHub Actions security.yml (no changes needed to run step)

```yaml
- name: Run pip-audit
  run: pixi run --environment lint pip-audit
```

The task definition handles flag injection automatically.

### Verification command

```bash
pixi run --environment lint pip-audit --version
# Should show: ✨ Pixi task (pip-audit in lint): pip-audit --min-severity high --version
```

## Notes

- `--min-severity high` filters to HIGH and CRITICAL only
- Alternative: `--min-severity critical` for critical-only
- pip-audit also supports `--ignore-vuln GHSA-xxx-yyy-zzz` for ignoring specific advisories
- The pixi task approach is preferable to hardcoding flags in workflow YAML because it keeps CI logic in `pixi.toml` (single source of truth)
